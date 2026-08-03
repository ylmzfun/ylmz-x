#pragma once

#include <functional>
#include <unordered_map>
#include <cstdint>

#ifdef YLMZ_PLATFORM_LINUX
#include <sys/epoll.h>
#endif

#ifdef YLMZ_PLATFORM_MACOS
#include <sys/event.h>
#include <sys/types.h>
// Define EPOLL-like constants for macOS
#define EPOLLIN  1
#define EPOLLOUT 2
#define EPOLLPRI 4
#define EPOLLERR 8
#define EPOLLHUP 16
#endif

namespace ylmz {

class EventLoop {
public:
    using EventCallback = std::function<void(uint32_t events)>;

    EventLoop();
    ~EventLoop();

    EventLoop(const EventLoop&) = delete;
    EventLoop& operator=(const EventLoop&) = delete;

    // Add a file descriptor with interest in events (EPOLLIN, EPOLLOUT)
    void add_fd(int fd, uint32_t events, EventCallback cb);

    // Modify events for a file descriptor
    void mod_fd(int fd, uint32_t events);

    // Remove a file descriptor
    void del_fd(int fd);

    // Run the event loop (blocks until stop() is called)
    void run();

    // Stop the event loop
    void stop();

private:
    int epfd_;
    bool running_;
    std::unordered_map<int, EventCallback> callbacks_;
    static const int MAX_EVENTS = 1024;
};

// Utility: set socket to non-blocking
void set_nonblocking(int fd);

// Utility: create a listening socket
int create_listen_socket(const char* host, int port, int backlog = 128);

} // namespace ylmz
