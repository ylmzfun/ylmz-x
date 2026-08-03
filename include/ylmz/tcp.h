#pragma once

#include <string>
#include <functional>
#include <memory>

namespace ylmz {

class EventLoop;

// TCP connection
class TCPConn {
public:
    friend class TCPServer;
    using DataHandler = std::function<void(TCPConn*, const char* data, size_t len)>;
    using CloseHandler = std::function<void(TCPConn*)>;

    TCPConn(int fd, EventLoop* loop);
    ~TCPConn();

    // Send data to client
    void Send(const std::string& data);
    void Send(const char* data, size_t len);

    // Close connection
    void Close();

    // Set handlers
    void OnData(DataHandler handler);
    void OnClose(CloseHandler handler);

    int fd() const { return fd_; }

    // Store user-defined context
    void SetUserData(void* data) { user_data_ = data; }
    void* GetUserData() const { return user_data_; }

private:
    int fd_;
    EventLoop* loop_;
    bool closed_ = false;
    void* user_data_ = nullptr;

    DataHandler on_data_;
    CloseHandler on_close_;

    std::string write_buf_;
    bool writing_ = false;

    void handle_read();
    void handle_write();
    void do_write();
};

// TCP server
class TCPServer {
public:
    using ConnectionHandler = std::function<void(TCPConn*)>;

    TCPServer(EventLoop* loop);
    ~TCPServer();

    // Start listening
    bool Listen(const std::string& host, int port);

    // Set new connection handler
    void OnConnection(ConnectionHandler handler);

private:
    EventLoop* loop_;
    int listen_fd_ = -1;
    ConnectionHandler on_connection_;

    void handle_accept();
};

} // namespace ylmz
