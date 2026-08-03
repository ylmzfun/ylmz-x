// Package websocket provides WebSocket support for the ylmz framework.
package websocket

import (
	"bufio"
	"crypto/sha1"
	"encoding/base64"
	"encoding/json"
	"errors"
	"io"
	"net"
	"net/http"
	"sync"
	"time"

	"github.com/ylmzfun/ylmz-go/ylmz"
)

const (
	wsGUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

	// Opcodes
	opText   = 1
	opBinary = 2
	opClose  = 8
	opPing   = 9
	opPong   = 10
)

// Conn represents a WebSocket connection.
type Conn struct {
	conn   net.Conn
	reader *bufio.Reader
	mu     sync.Mutex

	// Read timeout
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
}

// Message represents a WebSocket message.
type Message struct {
	Type int    // 1 = Text, 2 = Binary
	Data []byte
}

// Upgrade upgrades an HTTP connection to WebSocket.
func Upgrade(c *ylmz.Context) (*Conn, error) {
	if !c.IsWebsocket() {
		return nil, errors.New("not a websocket request")
	}

	key := c.GetHeader("Sec-WebSocket-Key")
	if key == "" {
		return nil, errors.New("missing Sec-WebSocket-Key")
	}

	// Compute accept key
	h := sha1.New()
	h.Write([]byte(key + wsGUID))
	acceptKey := base64.StdEncoding.EncodeToString(h.Sum(nil))

	// Hijack connection
	hj, ok := c.Writer.(http.Hijacker)
	if !ok {
		return nil, errors.New("server does not support hijacking")
	}
	conn, bufrw, err := hj.Hijack()
	if err != nil {
		return nil, err
	}

	// Send upgrade response
	response := "HTTP/1.1 101 Switching Protocols\r\n" +
		"Upgrade: websocket\r\n" +
		"Connection: Upgrade\r\n" +
		"Sec-WebSocket-Accept: " + acceptKey + "\r\n\r\n"

	if _, err := bufrw.WriteString(response); err != nil {
		conn.Close()
		return nil, err
	}
	if err := bufrw.Flush(); err != nil {
		conn.Close()
		return nil, err
	}

	return &Conn{
		conn:   conn,
		reader: bufrw.Reader,
	}, nil
}

// ReadMessage reads a WebSocket message.
func (c *Conn) ReadMessage() (*Message, error) {
	if c.ReadTimeout > 0 {
		c.conn.SetReadDeadline(time.Now().Add(c.ReadTimeout))
	}

	// Read first 2 bytes
	header := make([]byte, 2)
	if _, err := io.ReadFull(c.reader, header); err != nil {
		return nil, err
	}

	fin := header[0]&0x80 != 0
	opcode := int(header[0] & 0x0F)
	masked := header[1]&0x80 != 0
	length := int64(header[1] & 0x7F)

	// Extended payload length
	switch {
	case length == 126:
		ext := make([]byte, 2)
		if _, err := io.ReadFull(c.reader, ext); err != nil {
			return nil, err
		}
		length = int64(ext[0])<<8 | int64(ext[1])
	case length == 127:
		ext := make([]byte, 8)
		if _, err := io.ReadFull(c.reader, ext); err != nil {
			return nil, err
		}
		length = int64(ext[0])<<56 | int64(ext[1])<<48 |
			int64(ext[2])<<40 | int64(ext[3])<<32 |
			int64(ext[4])<<24 | int64(ext[5])<<16 |
			int64(ext[6])<<8 | int64(ext[7])
	}

	// Read mask key
	var maskKey []byte
	if masked {
		maskKey = make([]byte, 4)
		if _, err := io.ReadFull(c.reader, maskKey); err != nil {
			return nil, err
		}
	}

	// Read payload
	payload := make([]byte, length)
	if _, err := io.ReadFull(c.reader, payload); err != nil {
		return nil, err
	}

	// Unmask
	if masked {
		for i := range payload {
			payload[i] ^= maskKey[i%4]
		}
	}

	// Handle control frames
	switch opcode {
	case opClose:
		c.writeFrame(opClose, nil)
		return nil, io.EOF
	case opPing:
		c.writeFrame(opPong, payload)
		return c.ReadMessage()
	case opPong:
		return c.ReadMessage()
	}

	_ = fin // silence unused warning
	return &Message{Type: opcode, Data: payload}, nil
}

// WriteMessage writes a WebSocket message.
func (c *Conn) WriteMessage(msgType int, data []byte) error {
	return c.writeFrame(msgType, data)
}

// WriteJSON writes JSON data.
func (c *Conn) WriteJSON(v any) error {
	data, err := json.Marshal(v)
	if err != nil {
		return err
	}
	return c.writeFrame(opText, data)
}

// ReadJSON reads JSON data.
func (c *Conn) ReadJSON(v any) error {
	msg, err := c.ReadMessage()
	if err != nil {
		return err
	}
	return json.Unmarshal(msg.Data, v)
}

// Close closes the connection.
func (c *Conn) Close() error {
	return c.conn.Close()
}

func (c *Conn) writeFrame(opcode int, payload []byte) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.WriteTimeout > 0 {
		c.conn.SetWriteDeadline(time.Now().Add(c.WriteTimeout))
	}

	var frame []byte
	frame = append(frame, 0x80|byte(opcode)) // FIN + opcode

	length := len(payload)
	switch {
	case length <= 125:
		frame = append(frame, byte(length))
	case length <= 65535:
		frame = append(frame, 126)
		frame = append(frame, byte(length>>8), byte(length))
	default:
		frame = append(frame, 127)
		for i := 7; i >= 0; i-- {
			frame = append(frame, byte(length>>(i*8)))
		}
	}

	frame = append(frame, payload...)
	_, err := c.conn.Write(frame)
	return err
}

// Handler returns a WebSocket handler that upgrades and calls the callback.
func Handler(callback func(*Conn) error) ylmz.HandlerFunc {
	return func(c *ylmz.Context) {
		conn, err := Upgrade(c)
		if err != nil {
			c.String(400, "websocket upgrade failed: %v", err)
			return
		}
		defer conn.Close()

		if err := callback(conn); err != nil {
			return
		}
	}
}
