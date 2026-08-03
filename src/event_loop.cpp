#include "ylmz/event_loop.h"

#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdexcept>
#include <iostream>

#ifdef YLMZ_PLATFORM_MACOS
#include <sys/event.h>
#endif

namespace ylmz {

// ============================================================
// EventLoop
// ============================================================

EventLoop::EventLoop() : running_(false) {
#ifdef YLMZ_PLATFORM_LINUX
    epfd_ = epoll_create1(0);
    if (epfd_ < 0) {
        throw std::runtime_error("epoll_create1 failed: " + std::string(strerror(errno)));
    }
#elif defined(YLMZ_PLATFORM_MACOS)
    epfd_ = kqueue();
    if (epfd_ < 0) {
        throw std::runtime_error("kqueue failed: " + std::string(strerror(errno)));
    }
#endif
}

EventLoop::~EventLoop() {
    if (epfd_ >= 0) {
        close(epfd_);
    }
}

void EventLoop::add_fd(int fd, uint32_t events, EventCallback cb) {
    callbacks_[fd] = std::move(cb);

#ifdef YLMZ_PLATFORM_LINUX
    struct epoll_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.events = events;
    ev.data.fd = fd;
    if (epoll_ctl(epfd_, EPOLL_CTL_ADD, fd, &ev) < 0) {
        callbacks_.erase(fd);
        throw std::runtime_error("epoll_ctl ADD fd=" + std::to_string(fd) +
                                 " failed: " + strerror(errno));
    }
#elif defined(YLMZ_PLATFORM_MACOS)
    struct kevent ev_set[2];
    int n = 0;
    if (events & (EPOLLIN | EPOLLPRI)) {
        EV_SET(&ev_set[n++], fd, EVFILT_READ, EV_ADD | EV_ENABLE, 0, 0, nullptr);
    }
    if (events & EPOLLOUT) {
        EV_SET(&ev_set[n++], fd, EVFILT_WRITE, EV_ADD | EV_ENABLE, 0, 0, nullptr);
    }
    if (kevent(epfd_, ev_set, n, nullptr, 0, nullptr) < 0) {
        callbacks_.erase(fd);
        throw std::runtime_error("kevent ADD fd=" + std::to_string(fd) +
                                 " failed: " + strerror(errno));
    }
#endif
}

void EventLoop::mod_fd(int fd, uint32_t events) {
#ifdef YLMZ_PLATFORM_LINUX
    struct epoll_event ev;
    memset(&ev, 0, sizeof(ev));
    ev.events = events;
    ev.data.fd = fd;
    if (epoll_ctl(epfd_, EPOLL_CTL_MOD, fd, &ev) < 0) {
        // If MOD fails (fd not registered), try ADD
        if (errno == ENOENT) {
            if (epoll_ctl(epfd_, EPOLL_CTL_ADD, fd, &ev) < 0) {
                throw std::runtime_error("epoll_ctl ADD (fallback) fd=" +
                                         std::to_string(fd) + " failed: " + strerror(errno));
            }
            return;
        }
        throw std::runtime_error("epoll_ctl MOD fd=" + std::to_string(fd) +
                                 " failed: " + strerror(errno));
    }
#elif defined(YLMZ_PLATFORM_MACOS)
    struct kevent ev_set[2];
    int n = 0;
    if (events & (EPOLLIN | EPOLLPRI)) {
        EV_SET(&ev_set[n++], fd, EVFILT_READ, EV_ADD | EV_ENABLE, 0, 0, nullptr);
    } else {
        EV_SET(&ev_set[n++], fd, EVFILT_READ, EV_DELETE, 0, 0, nullptr);
    }
    if (events & EPOLLOUT) {
        EV_SET(&ev_set[n++], fd, EVFILT_WRITE, EV_ADD | EV_ENABLE, 0, 0, nullptr);
    } else {
        EV_SET(&ev_set[n++], fd, EVFILT_WRITE, EV_DELETE, 0, 0, nullptr);
    }
    if (kevent(epfd_, ev_set, n, nullptr, 0, nullptr) < 0) {
        throw std::runtime_error("kevent MOD fd=" + std::to_string(fd) +
                                 " failed: " + strerror(errno));
    }
#endif
}

void EventLoop::del_fd(int fd) {
    callbacks_.erase(fd);
#ifdef YLMZ_PLATFORM_LINUX
    epoll_ctl(epfd_, EPOLL_CTL_DEL, fd, nullptr);
#elif defined(YLMZ_PLATFORM_MACOS)
    struct kevent ev_set[2];
    EV_SET(&ev_set[0], fd, EVFILT_READ, EV_DELETE, 0, 0, nullptr);
    EV_SET(&ev_set[1], fd, EVFILT_WRITE, EV_DELETE, 0, 0, nullptr);
    kevent(epfd_, ev_set, 2, nullptr, 0, nullptr);
#endif
}

void EventLoop::run() {
    running_ = true;

#ifdef YLMZ_PLATFORM_LINUX
    struct epoll_event events[MAX_EVENTS];

    while (running_) {
        int nfds = epoll_wait(epfd_, events, MAX_EVENTS, -1);
        if (nfds < 0) {
            if (errno == EINTR) continue;
            break;
        }

        for (int i = 0; i < nfds; i++) {
            int fd = events[i].data.fd;
            auto it = callbacks_.find(fd);
            if (it != callbacks_.end()) {
                it->second(events[i].events);
            }
        }
    }
#elif defined(YLMZ_PLATFORM_MACOS)
    struct kevent events[MAX_EVENTS];

    while (running_) {
        int nfds = kevent(epfd_, nullptr, 0, events, MAX_EVENTS, nullptr);
        if (nfds < 0) {
            if (errno == EINTR) continue;
            break;
        }

        for (int i = 0; i < nfds; i++) {
            int fd = static_cast<int>(events[i].ident);
            auto it = callbacks_.find(fd);
            if (it != callbacks_.end()) {
                uint32_t flags = 0;
                if (events[i].filter == EVFILT_READ) flags |= EPOLLIN;
                if (events[i].filter == EVFILT_WRITE) flags |= EPOLLOUT;
                // Check for errors
                if (events[i].flags & EV_ERROR) flags |= EPOLLERR;
                if (events[i].flags & EV_EOF) flags |= EPOLLHUP;
                it->second(flags);
            }
        }
    }
#endif
}

void EventLoop::stop() {
    running_ = false;
}

// ============================================================
// Utilities
// ============================================================

void set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) {
        throw std::runtime_error("fcntl F_GETFL failed: " + std::string(strerror(errno)));
    }
    if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) {
        throw std::runtime_error("fcntl F_SETFL O_NONBLOCK failed: " + std::string(strerror(errno)));
    }
}

int create_listen_socket(const char* host, int port, int backlog) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        throw std::runtime_error("socket() failed: " + std::string(strerror(errno)));
    }

    int opt = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    // Also set SO_REUSEPORT for macOS
#ifdef SO_REUSEPORT
    setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &opt, sizeof(opt));
#endif

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);

    if (host && host[0] != '\0' && strcmp(host, "0.0.0.0") != 0) {
        if (inet_pton(AF_INET, host, &addr.sin_addr) <= 0) {
            close(fd);
            throw std::runtime_error("inet_pton failed for host: " + std::string(host));
        }
    } else {
        addr.sin_addr.s_addr = INADDR_ANY;
    }

    if (bind(fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close(fd);
        throw std::runtime_error("bind() " + std::string(host) + ":" + std::to_string(port) +
                                 " failed: " + strerror(errno));
    }

    if (listen(fd, backlog) < 0) {
        close(fd);
        throw std::runtime_error("listen() failed: " + std::string(strerror(errno)));
    }

    set_nonblocking(fd);
    return fd;
}

} // namespace ylmz
