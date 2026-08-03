#pragma once

#include <string>
#include <map>
#include <vector>
#include <functional>

namespace ylmz {

class Context;

// Handler function type
using HandlerFunc = std::function<void(Context*)>;

// Middleware function type: receives context and calls next() to proceed
using MiddlewareFunc = std::function<void(Context*)>;

// Radix tree node
struct RadixNode {
    std::string path;                     // path segment at this node
    std::string indices;                  // first chars of children (for fast lookup)
    std::vector<RadixNode*> children;
    std::map<std::string, HandlerFunc> handlers; // method -> handler
    bool wildcard = false;                // true for *wildcard nodes
    std::string param_name;               // name for :param nodes

    ~RadixNode();
    RadixNode* find_child(char c) const;
    void add_child(RadixNode* child);
};

// Router using radix tree (same algorithm as Gin/httprouter)
class Router {
public:
    Router();
    ~Router();

    // Register a handler for method + path
    // Path supports: /static/path, /:param, /*wildcard
    void add_route(const std::string& method, const std::string& path, HandlerFunc handler);

    // Find a handler for method + path, fills params map
    HandlerFunc find(const std::string& method, const std::string& path,
                     std::map<std::string, std::string>& params) const;

    // Route group (prefix support)
    class Group {
    public:
        Group(Router* router, std::string prefix)
            : router_(router), prefix_(std::move(prefix)) {}

        void GET(const std::string& path, HandlerFunc handler) {
            router_->add_route("GET", prefix_ + path, std::move(handler));
        }
        void POST(const std::string& path, HandlerFunc handler) {
            router_->add_route("POST", prefix_ + path, std::move(handler));
        }
        void PUT(const std::string& path, HandlerFunc handler) {
            router_->add_route("PUT", prefix_ + path, std::move(handler));
        }
        void DELETE(const std::string& path, HandlerFunc handler) {
            router_->add_route("DELETE", prefix_ + path, std::move(handler));
        }
        void PATCH(const std::string& path, HandlerFunc handler) {
            router_->add_route("PATCH", prefix_ + path, std::move(handler));
        }
        void HEAD(const std::string& path, HandlerFunc handler) {
            router_->add_route("HEAD", prefix_ + path, std::move(handler));
        }
        void OPTIONS(const std::string& path, HandlerFunc handler) {
            router_->add_route("OPTIONS", prefix_ + path, std::move(handler));
        }

        Group SubGroup(const std::string& prefix) {
            return Group(router_, prefix_ + prefix);
        }

    private:
        Router* router_;
        std::string prefix_;
    };

    // Shorthand for registering routes directly on the router
    void GET(const std::string& path, HandlerFunc handler) {
        add_route("GET", path, std::move(handler));
    }
    void POST(const std::string& path, HandlerFunc handler) {
        add_route("POST", path, std::move(handler));
    }
    void PUT(const std::string& path, HandlerFunc handler) {
        add_route("PUT", path, std::move(handler));
    }
    void DELETE(const std::string& path, HandlerFunc handler) {
        add_route("DELETE", path, std::move(handler));
    }
    void PATCH(const std::string& path, HandlerFunc handler) {
        add_route("PATCH", path, std::move(handler));
    }
    void HEAD(const std::string& path, HandlerFunc handler) {
        add_route("HEAD", path, std::move(handler));
    }
    void OPTIONS(const std::string& path, HandlerFunc handler) {
        add_route("OPTIONS", path, std::move(handler));
    }

    // Create a route group with prefix
    Group CreateGroup(const std::string& prefix) {
        return Group(this, prefix);
    }

private:
    RadixNode* root_;

    void insert_node(RadixNode* node, const std::string& method,
                     const std::string& full_path, size_t pos, HandlerFunc handler);
    HandlerFunc search_node(RadixNode* node, const std::string& full_path,
                            size_t pos, std::map<std::string, std::string>& params) const;
};

} // namespace ylmz
