#include "ylmz/context.h"
#include "ylmz/http_parser.h"

#include <unistd.h>
#include <cstring>
#include <sstream>
#include <ctime>
#include <iomanip>

namespace ylmz {

Context::Context(int fd) : fd_(fd) {}

// --- Request accessors ---

const std::string& Context::Method() const { return method_; }
const std::string& Context::Path() const { return path_; }
const std::string& Context::Version() const { return version_; }

std::string Context::GetHeader(const std::string& key) const {
    auto it = headers_.find(key);
    if (it != headers_.end()) return it->second;
    // Case-insensitive lookup
    std::string lower = key;
    for (auto& c : lower) c = tolower(c);
    it = headers_.find(lower);
    return (it != headers_.end()) ? it->second : "";
}

const std::map<std::string, std::string>& Context::Headers() const {
    return headers_;
}

const std::string& Context::Body() const {
    return body_;
}

std::string Context::Param(const std::string& key) const {
    auto it = params_.find(key);
    return (it != params_.end()) ? it->second : "";
}

std::string Context::Query(const std::string& key) const {
    if (query_cache_.empty() && !query_string_.empty()) {
        parse_query_string();
    }
    auto it = query_cache_.find(key);
    return (it != query_cache_.end()) ? it->second : "";
}

// --- Response ---

void Context::SetStatus(int code) {
    status_code_ = code;
}

void Context::SetHeader(const std::string& key, const std::string& value) {
    resp_headers_[key] = value;
}

void Context::String(int code, const std::string& s) {
    SetStatus(code);
    write_response("text/plain; charset=utf-8", s);
}

void Context::JSON(int code, const json& data) {
    SetStatus(code);
    write_response("application/json; charset=utf-8", data.dump());
}

void Context::HTML(int code, const std::string& html) {
    SetStatus(code);
    write_response("text/html; charset=utf-8", html);
}

void Context::Data(int code, const std::string& content_type, const std::string& data) {
    SetStatus(code);
    write_response(content_type, data);
}

// --- Internal ---

void Context::set_request(const HttpRequest& req) {
    method_ = req.method;
    path_ = req.path;
    version_ = req.version;
    headers_ = req.headers;
    body_ = req.body;

    // Extract query string from path
    size_t qpos = path_.find('?');
    if (qpos != std::string::npos) {
        query_string_ = path_.substr(qpos + 1);
        path_ = path_.substr(0, qpos);
    }
    query_cache_.clear();
}

void Context::set_params(std::map<std::string, std::string> params) {
    params_ = std::move(params);
}

void Context::set_middlewares(std::vector<std::function<void(Context*)>>* mws) {
    middlewares_ = mws;
    middleware_index_ = 0;
}

void Context::Next() {
    if (!middlewares_) return;

    if (middleware_index_ < middlewares_->size()) {
        auto mw = (*middlewares_)[middleware_index_++];
        mw(this);
    }
}

void Context::parse_query_string() const {
    const auto& qs = query_string_;
    size_t pos = 0;
    while (pos < qs.size()) {
        size_t eq = qs.find('=', pos);
        size_t amp = qs.find('&', pos);
        if (amp == std::string::npos) amp = qs.size();

        if (eq != std::string::npos && eq < amp) {
            std::string key = qs.substr(pos, eq - pos);
            std::string val = qs.substr(eq + 1, amp - eq - 1);
            query_cache_[key] = val;
        }
        pos = amp + 1;
    }
}

static const char* status_text(int code) {
    switch (code) {
    case 200: return "OK";
    case 201: return "Created";
    case 204: return "No Content";
    case 301: return "Moved Permanently";
    case 302: return "Found";
    case 304: return "Not Modified";
    case 400: return "Bad Request";
    case 401: return "Unauthorized";
    case 403: return "Forbidden";
    case 404: return "Not Found";
    case 405: return "Method Not Allowed";
    case 500: return "Internal Server Error";
    case 502: return "Bad Gateway";
    case 503: return "Service Unavailable";
    default:  return "Unknown";
    }
}

void Context::write_response(const std::string& content_type, const std::string& data) {
    if (responded_) return;
    responded_ = true;

    // Build HTTP response
    std::ostringstream resp;
    resp << "HTTP/1.1 " << status_code_ << " " << status_text(status_code_) << "\r\n";
    resp << "Content-Type: " << content_type << "\r\n";
    resp << "Content-Length: " << data.size() << "\r\n";
    resp << "Connection: keep-alive\r\n";

    for (auto& [key, val] : resp_headers_) {
        resp << key << ": " << val << "\r\n";
    }

    resp << "\r\n";
    resp << data;

    std::string resp_str = resp.str();
    size_t written = 0;
    while (written < resp_str.size()) {
        ssize_t n = write(fd_, resp_str.data() + written, resp_str.size() - written);
        if (n < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                // Would block - response will be written later via event loop
                break;
            }
            break; // error
        }
        written += n;
    }
}

} // namespace ylmz
