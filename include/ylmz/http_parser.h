#pragma once

#include <string>
#include <map>
#include <vector>
#include <cstdint>

namespace ylmz {

// HTTP request parsed result
struct HttpRequest {
    std::string method;
    std::string path;
    std::string version;
    std::map<std::string, std::string> headers;
    std::string body;

    void reset() {
        method.clear();
        path.clear();
        version.clear();
        headers.clear();
        body.clear();
    }
};

// HTTP/1.1 parser using state machine
class HttpParser {
public:
    HttpParser();

    // Feed data into parser. Returns number of bytes consumed.
    // When a complete request is parsed, calls the callback.
    using RequestCallback = std::function<void(HttpRequest&)>;

    void set_callback(RequestCallback cb);
    size_t parse(const char* data, size_t len);
    void reset();

    bool is_complete() const { return complete_; }

private:
    enum State {
        REQ_METHOD,
        REQ_SPACE_BEFORE_URL,
        REQ_URL,
        REQ_SPACE_BEFORE_VER,
        REQ_VERSION,
        REQ_CR,
        REQ_LF,
        HEADER_KEY,
        HEADER_SPACE_BEFORE_VAL,
        HEADER_VAL,
        HEADER_CR,
        HEADER_LF,
        HEADER_END_CR,
        HEADER_END_LF,
        BODY,
        DONE
    };

    State state_;
    HttpRequest req_;
    RequestCallback callback_;
    bool complete_;

    std::string cur_key_;
    std::string cur_val_;
    size_t content_length_;
    size_t body_read_;

    void on_request_complete();
};

} // namespace ylmz
