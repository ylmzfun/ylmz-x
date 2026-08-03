#pragma once

#include <string>
#include <functional>
#include <vector>
#include <cstdint>
#include <memory>

namespace ylmz {

// WebSocket connection
class WSConn {
public:
    using MessageHandler = std::function<void(WSConn*, const std::string&)>;
    using BinaryHandler = std::function<void(WSConn*, const std::vector<uint8_t>&)>;
    using CloseHandler = std::function<void(WSConn*)>;

    WSConn(int fd);
    ~WSConn();

    // Send a text message
    void Send(const std::string& message);

    // Send a binary message
    void SendBinary(const std::vector<uint8_t>& data);

    // Close the connection
    void Close();

    // Set message handlers
    void OnMessage(MessageHandler handler);
    void OnBinary(BinaryHandler handler);
    void OnClose(CloseHandler handler);

    // Internal: feed received data into the WebSocket parser
    void feed_data(const char* data, size_t len);

    int fd() const { return fd_; }
    bool is_closed() const { return closed_; }

private:
    int fd_;
    bool closed_ = false;

    MessageHandler on_message_;
    BinaryHandler on_binary_;
    CloseHandler on_close_;

    // Frame parsing state
    enum OpCode {
        OP_CONT  = 0x0,
        OP_TEXT  = 0x1,
        OP_BIN   = 0x2,
        OP_CLOSE = 0x8,
        OP_PING  = 0x9,
        OP_PONG  = 0xA,
    };

    std::vector<uint8_t> recv_buf_;
    bool mask_flag_ = false;
    uint8_t masking_key_[4];
    size_t payload_len_ = 0;

    void parse_frame();
    void send_frame(uint8_t opcode, const uint8_t* data, size_t len, bool masked = false);
    void handle_ping(const std::vector<uint8_t>& data);
    void handle_pong();
    void handle_close();
};

// WebSocket upgrader: performs HTTP upgrade handshake
class WSUpgrader {
public:
    static bool try_upgrade(int fd, const std::string& request_headers,
                            std::string& accept_key);
};

} // namespace ylmz
