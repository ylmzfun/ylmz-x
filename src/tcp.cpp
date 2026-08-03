#include "ylmz/tcp.h"
#include "ylmz/event_loop.h"

#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <cstring>
#include <stdexcept>

namespace ylmz {

// ============================================================
// TCPConn
// ============================================================

TCPConn::TCPConn(int fd, EventLoop* loop) : fd_(fd), loop_(loop) {
    set_nonblocking(fd);
}

TCPConn::~TCPConn() {
    if (!closed_ && fd_ >= 0) {
        Close();
    }
}

void TCPConn::OnData(DataHandler handler) { on_data_ = std::move(handler); }
void TCPConn::OnClose(CloseHandler handler) { on_close_ = std::move(handler); }

void TCPConn::Send(const std::string& data) {
    Send(data.data(), data.size());
}

void TCPConn::Send(const char* data, size_t len) {
    if (closed_ || fd_ < 0) return;

    write_buf_.append(data, len);

    if (!writing_) {
        do_write();
    }
}

void TCPConn::Close() {
    if (!closed_) {
        closed_ = true;
        loop_->del_fd(fd_);
        if (on_close_) on_close_(this);
        if (fd_ >= 0) {
            close(fd_);
            fd_ = -1;
        }
    }
}

void TCPConn::handle_read() {
    char buf[65536];
    while (true) {
        ssize_t n = read(fd_, buf, sizeof(buf));
        if (n > 0) {
            if (on_data_) on_data_(this, buf, n);
        } else if (n == 0) {
            Close();
            break;
        } else {
            if (errno == EAGAIN || errno == EWOULDBLOCK) break;
            Close();
            break;
        }
    }
}

void TCPConn::handle_write() {
    writing_ = false;
    do_write();
}

void TCPConn::do_write() {
    if (write_buf_.empty()) return;

    writing_ = true;
    ssize_t n = write(fd_, write_buf_.data(), write_buf_.size());
    if (n > 0) {
        write_buf_.erase(0, n);
        if (write_buf_.empty()) {
            writing_ = false;
            loop_->mod_fd(fd_, EPOLLIN);
        }
    } else if (n < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
        Close();
    }
}

// ============================================================
// TCPServer
// ============================================================

TCPServer::TCPServer(EventLoop* loop) : loop_(loop) {}

TCPServer::~TCPServer() {
    if (listen_fd_ >= 0) {
        loop_->del_fd(listen_fd_);
        close(listen_fd_);
    }
}

bool TCPServer::Listen(const std::string& host, int port) {
    try {
        listen_fd_ = create_listen_socket(host.c_str(), port);
    } catch (const std::exception& e) {
        fprintf(stderr, "TCP Listen failed: %s\n", e.what());
        return false;
    }

    auto self = this;
    loop_->add_fd(listen_fd_, EPOLLIN, [self](uint32_t) {
        self->handle_accept();
    });

    return true;
}

void TCPServer::OnConnection(ConnectionHandler handler) {
    on_connection_ = std::move(handler);
}

void TCPServer::handle_accept() {
    while (true) {
        struct sockaddr_in addr;
        socklen_t addr_len = sizeof(addr);
        int client_fd = accept(listen_fd_, (struct sockaddr*)&addr, &addr_len);
        if (client_fd < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) break;
            break;
        }

        set_nonblocking(client_fd);
        auto* conn = new TCPConn(client_fd, loop_);

        // Set up read callback
        auto* conn_ptr = conn;
        loop_->add_fd(client_fd, EPOLLIN, [conn_ptr](uint32_t events) {
            if (events & (EPOLLIN | EPOLLPRI)) {
                conn_ptr->handle_read();
            }
            if (events & EPOLLOUT) {
                conn_ptr->handle_write();
            }
            if (events & (EPOLLERR | EPOLLHUP)) {
                conn_ptr->Close();
            }
        });

        if (on_connection_) on_connection_(conn);
    }
}

} // namespace ylmz
