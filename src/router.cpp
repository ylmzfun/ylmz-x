#include "ylmz/router.h"
#include <algorithm>
#include <iostream>

namespace ylmz {

// ============================================================
// RadixNode
// ============================================================

RadixNode::~RadixNode() {
    for (auto* child : children) {
        delete child;
    }
}

RadixNode* RadixNode::find_child(char c) const {
    for (auto* child : children) {
        if (!child->path.empty() && child->path[0] == c) {
            return child;
        }
    }
    return nullptr;
}

void RadixNode::add_child(RadixNode* child) {
    children.push_back(child);
    if (!child->path.empty()) {
        indices += child->path[0];
    }
}

// ============================================================
// Router
// ============================================================

Router::Router() : root_(new RadixNode()) {
    root_->path = "/";
}

Router::~Router() {
    delete root_;
}

void Router::add_route(const std::string& method, const std::string& path,
                       HandlerFunc handler) {
    if (path.empty() || path[0] != '/') {
        return; // invalid path
    }
    insert_node(root_, method, path, 0, std::move(handler));
}

HandlerFunc Router::find(const std::string& method, const std::string& path,
                         std::map<std::string, std::string>& params) const {
    params.clear();
    return search_node(root_, path, 0, params);
}

// --- Insertion ---

void Router::insert_node(RadixNode* node, const std::string& method,
                         const std::string& full_path, size_t pos, HandlerFunc handler) {
    // Skip leading '/'
    while (pos < full_path.size() && full_path[pos] == '/') pos++;

    if (pos >= full_path.size()) {
        // End of path: store handler at this node
        node->handlers[method] = std::move(handler);
        return;
    }

    // Extract the next segment
    size_t seg_start = pos;
    bool is_param = false;
    bool is_wildcard = false;

    if (full_path[pos] == ':') {
        is_param = true;
        pos++; // skip ':'
        seg_start = pos;
    } else if (full_path[pos] == '*') {
        is_wildcard = true;
        pos++; // skip '*'
        seg_start = pos;
    }

    while (pos < full_path.size() && full_path[pos] != '/') pos++;

    std::string segment = full_path.substr(seg_start, pos - seg_start);
    std::string full_segment = full_path.substr(seg_start - (is_param ? 1 : 0) - (is_wildcard ? 1 : 0),
                                                pos - seg_start + (is_param ? 1 : 0) + (is_wildcard ? 1 : 0));

    // Find matching child
    RadixNode* child = nullptr;
    for (auto* c : node->children) {
        if (is_wildcard && c->wildcard) {
            child = c;
            break;
        }
        if (is_param && c->path[0] == ':') {
            child = c;
            break;
        }
        if (!is_param && !is_wildcard && c->path == segment) {
            child = c;
            break;
        }
    }

    if (child == nullptr) {
        // Create new child node
        auto* new_node = new RadixNode();
        if (is_wildcard) {
            new_node->path = "*" + segment;
            new_node->wildcard = true;
            new_node->param_name = segment;
        } else if (is_param) {
            new_node->path = ":" + segment;
            new_node->param_name = segment;
        } else {
            new_node->path = segment;
        }
        node->add_child(new_node);
        child = new_node;
    }

    // Continue insertion from child
    // For wildcard, consume the rest
    if (is_wildcard) {
        child->handlers[method] = std::move(handler);
        return;
    }

    insert_node(child, method, full_path, pos, std::move(handler));
}

// --- Search ---

HandlerFunc Router::search_node(RadixNode* node, const std::string& full_path,
                                size_t pos,
                                std::map<std::string, std::string>& params) const {
    // Skip leading '/'
    while (pos < full_path.size() && full_path[pos] == '/') pos++;

    // Extract the next segment
    if (pos >= full_path.size()) {
        // End of path: look for handler with any method or specific method
        // Return handler - caller will check method
        auto it = node->handlers.find("GET"); // default to any
        if (it != node->handlers.end()) {
            // We need method-specific search
        }
        // Just return the first handler found; App layer handles method matching
        for (auto& [method, handler] : node->handlers) {
            return handler;
        }
        return nullptr;
    }

    size_t seg_start = pos;
    while (pos < full_path.size() && full_path[pos] != '/') pos++;
    std::string segment = full_path.substr(seg_start, pos - seg_start);

    // First try exact match
    for (auto* child : node->children) {
        if (!child->wildcard && child->path[0] != ':' && child->path == segment) {
            auto result = search_node(child, full_path, pos, params);
            if (result) return result;
        }
    }

    // Then try param match (:param)
    for (auto* child : node->children) {
        if (child->path[0] == ':') {
            auto result = search_node(child, full_path, pos, params);
            if (result) {
                params[child->param_name] = segment;
                return result;
            }
        }
    }

    // Then try wildcard match (*wildcard)
    for (auto* child : node->children) {
        if (child->wildcard) {
            // Wildcard captures the rest of the path
            std::string wildcard_val = full_path.substr(seg_start);
            params[child->param_name] = wildcard_val;
            for (auto& [method, handler] : child->handlers) {
                return handler;
            }
        }
    }

    return nullptr;
}

} // namespace ylmz
