#include "ylmz/ws.h"

#include <unistd.h>
#include <cstring>
#include <algorithm>
#include <sstream>
#include <iomanip>
#include <iostream>

// ============================================================
// Minimal SHA1 implementation (no external dependencies)
// ============================================================
namespace {

struct SHA1 {
    uint32_t state[5];
    uint64_t count;
    uint8_t buffer[64];

    SHA1() { reset(); }

    void reset() {
        state[0] = 0x67452301;
        state[1] = 0xEFCDAB89;
        state[2] = 0x98BADCFE;
        state[3] = 0x10325476;
        state[4] = 0xC3D2E1F0;
        count = 0;
    }

    void update(const uint8_t* data, size_t len) {
        size_t i = static_cast<size_t>(count & 63);
        count += len * 8;

        if (i > 0) {
            size_t take = std::min(64 - i, len);
            memcpy(buffer + i, data, take);
            i += take;
            data += take;
            len -= take;
            if (i == 64) {
                transform(buffer);
                i = 0;
            }
        }

        while (len >= 64) {
            transform(data);
            data += 64;
            len -= 64;
        }

        if (len > 0) {
            memcpy(buffer + i, data, len);
        }
    }

    void finalize(uint8_t digest[20]) {
        uint8_t final_count[8];
        for (int i = 0; i < 8; i++) {
            final_count[i] = static_cast<uint8_t>((count >> ((7 - i) * 8)) & 0xFF);
        }

        uint8_t pad = 0x80;
        update(&pad, 1);

        while ((count & 511) != 448) {
            uint8_t zero = 0;
            update(&zero, 1);
        }

        update(final_count, 8);

        for (int i = 0; i < 5; i++) {
            digest[i * 4]     = (state[i] >> 24) & 0xFF;
            digest[i * 4 + 1] = (state[i] >> 16) & 0xFF;
            digest[i * 4 + 2] = (state[i] >> 8)  & 0xFF;
            digest[i * 4 + 3] = state[i] & 0xFF;
        }
    }

private:
    static uint32_t rotl32(uint32_t x, int n) {
        return (x << n) | (x >> (32 - n));
    }

    void transform(const uint8_t* block) {
        uint32_t w[80];
        for (int i = 0; i < 16; i++) {
            w[i] = (block[i * 4] << 24) | (block[i * 4 + 1] << 16) |
                   (block[i * 4 + 2] << 8) | block[i * 4 + 3];
        }
        for (int i = 16; i < 80; i++) {
            w[i] = rotl32(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);
        }

        uint32_t a = state[0], b = state[1], c = state[2], d = state[3], e = state[4];

        for (int i = 0; i < 80; i++) {
            uint32_t f, k;
            if (i < 20) {
                f = (b & c) | (~b & d);
                k = 0x5A827999;
            } else if (i < 40) {
                f = b ^ c ^ d;
                k = 0x6ED9EBA1;
            } else if (i < 60) {
                f = (b & c) | (b & d) | (c & d);
                k = 0x8F1BBCDC;
            } else {
                f = b ^ c ^ d;
                k = 0xCA62C1D6;
            }
            uint32_t temp = rotl32(a, 5) + f + e + k + w[i];
            e = d;
            d = c;
            c = rotl32(b, 30);
            b = a;
            a = temp;
        }

        state[0] += a; state[1] += b; state[2] += c; state[3] += d; state[4] += e;
    }
};

// Base64 encoding
std::string base64_encode(const uint8_t* data, size_t len) {
    static const char* chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string result;
    result.reserve(((len + 2) / 3) * 4);

    for (size_t i = 0; i < len; i += 3) {
        uint32_t n = (static_cast<uint32_t>(data[i]) << 16);
        if (i + 1 < len) n |= (static_cast<uint32_t>(data[i + 1]) << 8);
        if (i + 2 < len) n |= static_cast<uint32_t>(data[i + 2]);

        result += chars[(n >> 18) & 0x3F];
        result += chars[(n >> 12) & 0x3F];
        result += (i + 1 < len) ? chars[(n >> 6) & 0x3F] : '=';
        result += (i + 2 < len) ? chars[n & 0x3F] : '=';
    }
    return result;
}

// WebSocket GUID for handshake
static const char* WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

} // anonymous namespace

namespace ylmz {

// ============================================================
// WSUpgrader
// ============================================================

bool WSUpgrader::try_upgrade(int fd, const std::string& request_headers,
                             std::string& accept_key) {
    // Find Sec-WebSocket-Key
    const char* key_header = "sec-websocket-key:";
    size_t pos = request_headers.find(key_header);
    if (pos == std::string::npos) {
        // Try with capital S
        key_header = "Sec-WebSocket-Key:";
        pos = request_headers.find(key_header);
    }
    if (pos == std::string::npos) {
        // Try in the raw headers map format
        auto key_pos = request_headers.find("sec-websocket-key");
        if (key_pos == std::string::npos) {
            key_pos = request_headers.find("Sec-WebSocket-Key");
        }
        if (key_pos == std::string::npos) return false;
        // Extract value between ": " and "\r\n"
        size_t val_start = request_headers.find(": ", key_pos);
        if (val_start == std::string::npos) return false;
        val_start += 2;
        size_t val_end = request_headers.find("\r\n", val_start);
        if (val_end == std::string::npos) return false;
        std::string key = request_headers.substr(val_start, val_end - val_start);
        // Trim
        while (!key.empty() && key.back() == ' ') key.pop_back();
        while (!key.empty() && key.front() == ' ') key.erase(0, 1);

        // Compute accept: SHA1(key + GUID) -> base64
        std::string combined = key + WS_GUID;
        SHA1 sha1;
        sha1.update(reinterpret_cast<const uint8_t*>(combined.data()), combined.size());
        uint8_t digest[20];
        sha1.finalize(digest);
        accept_key = base64_encode(digest, 20);

        // Send upgrade response
        std::ostringstream resp;
        resp << "HTTP/1.1 101 Switching Protocols\r\n";
        resp << "Upgrade: websocket\r\n";
        resp << "Connection: Upgrade\r\n";
        resp << "Sec-WebSocket-Accept: " << accept_key << "\r\n";
        resp << "\r\n";

        std::string resp_str = resp.str();
        size_t written = 0;
        while (written < resp_str.size()) {
            ssize_t n = write(fd, resp_str.data() + written, resp_str.size() - written);
            if (n <= 0) return false;
            written += n;
        }
        return true;
    }

    return false;
}

// ============================================================
// WSConn
// ============================================================

WSConn::WSConn(int fd) : fd_(fd) {}

WSConn::~WSConn() {
    if (!closed_ && fd_ >= 0) {
        close(fd_);
    }
}

void WSConn::OnMessage(MessageHandler handler) { on_message_ = std::move(handler); }
void WSConn::OnBinary(BinaryHandler handler) { on_binary_ = std::move(handler); }
void WSConn::OnClose(CloseHandler handler) { on_close_ = std::move(handler); }

void WSConn::Send(const std::string& message) {
    send_frame(OP_TEXT, reinterpret_cast<const uint8_t*>(message.data()), message.size(), false);
}

void WSConn::SendBinary(const std::vector<uint8_t>& data) {
    send_frame(OP_BIN, data.data(), data.size(), false);
}

void WSConn::Close() {
    if (!closed_) {
        send_frame(OP_CLOSE, nullptr, 0, false);
        closed_ = true;
        if (on_close_) on_close_(this);
        if (fd_ >= 0) {
            close(fd_);
            fd_ = -1;
        }
    }
}

void WSConn::feed_data(const char* data, size_t len) {
    recv_buf_.insert(recv_buf_.end(),
                     reinterpret_cast<const uint8_t*>(data),
                     reinterpret_cast<const uint8_t*>(data) + len);
    parse_frame();
}

void WSConn::send_frame(uint8_t opcode, const uint8_t* data, size_t len, bool masked) {
    if (fd_ < 0) return;

    std::vector<uint8_t> frame;
    frame.push_back(0x80 | opcode); // FIN + opcode

    if (len < 126) {
        frame.push_back(static_cast<uint8_t>(len));
    } else if (len <= 0xFFFF) {
        frame.push_back(126);
        frame.push_back((len >> 8) & 0xFF);
        frame.push_back(len & 0xFF);
    } else {
        frame.push_back(127);
        for (int i = 7; i >= 0; i--) {
            frame.push_back((len >> (i * 8)) & 0xFF);
        }
    }

    if (data && len > 0) {
        frame.insert(frame.end(), data, data + len);
    }

    size_t written = 0;
    while (written < frame.size()) {
        ssize_t n = write(fd_, frame.data() + written, frame.size() - written);
        if (n <= 0) break;
        written += n;
    }
}

void WSConn::parse_frame() {
    while (recv_buf_.size() >= 2) {
        uint8_t byte0 = recv_buf_[0];
        uint8_t byte1 = recv_buf_[1];
        bool fin = (byte0 & 0x80) != 0;
        uint8_t opcode = byte0 & 0x0F;
        mask_flag_ = (byte1 & 0x80) != 0;
        payload_len_ = byte1 & 0x7F;

        size_t header_size = 2;
        if (payload_len_ == 126) header_size += 2;
        else if (payload_len_ == 127) header_size += 8;
        if (mask_flag_) header_size += 4;

        if (recv_buf_.size() < header_size) return;

        // Read extended payload length
        if (payload_len_ == 126) {
            payload_len_ = (recv_buf_[2] << 8) | recv_buf_[3];
        } else if (payload_len_ == 127) {
            payload_len_ = 0;
            for (int i = 0; i < 8; i++) {
                payload_len_ = (payload_len_ << 8) | recv_buf_[2 + i];
            }
        }

        // Read masking key
        size_t mask_offset = header_size - (mask_flag_ ? 4 : 0);
        if (mask_flag_) {
            for (int i = 0; i < 4; i++) {
                masking_key_[i] = recv_buf_[mask_offset + i];
            }
        }

        // Need full payload
        if (recv_buf_.size() < header_size + payload_len_) return;

        // Extract payload
        std::vector<uint8_t> payload(
            recv_buf_.begin() + header_size,
            recv_buf_.begin() + header_size + payload_len_);

        // Unmask if needed
        if (mask_flag_) {
            for (size_t i = 0; i < payload.size(); i++) {
                payload[i] ^= masking_key_[i % 4];
            }
        }

        // Remove processed data
        recv_buf_.erase(recv_buf_.begin(),
                        recv_buf_.begin() + header_size + payload_len_);

        // Handle frame
        switch (opcode) {
        case OP_TEXT:
            if (on_message_) {
                std::string msg(payload.begin(), payload.end());
                on_message_(this, msg);
            }
            break;
        case OP_BIN:
            if (on_binary_) on_binary_(this, payload);
            break;
        case OP_CLOSE:
            handle_close();
            return; // connection closed
        case OP_PING:
            handle_ping(payload);
            break;
        case OP_PONG:
            handle_pong();
            break;
        case OP_CONT:
            // Continuation frame - accumulate (simplified)
            break;
        default:
            break;
        }

        if (!fin) {
            // Continuation expected, accumulate data
            // Simplified: treat each frame as complete
        }
    }
}

void WSConn::handle_ping(const std::vector<uint8_t>& data) {
    send_frame(OP_PONG, data.data(), data.size(), false);
}

void WSConn::handle_pong() {
    // Nothing special
}

void WSConn::handle_close() {
    if (!closed_) {
        closed_ = true;
        if (on_close_) on_close_(this);
    }
}

} // namespace ylmz
