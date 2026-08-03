#include "ylmz/http_parser.h"
#include <cstdlib>
#include <cstring>

namespace ylmz {

HttpParser::HttpParser()
    : state_(REQ_METHOD), complete_(false), content_length_(0), body_read_(0) {}

void HttpParser::set_callback(RequestCallback cb) {
    callback_ = std::move(cb);
}

void HttpParser::reset() {
    state_ = REQ_METHOD;
    complete_ = false;
    content_length_ = 0;
    body_read_ = 0;
    cur_key_.clear();
    cur_val_.clear();
    req_.reset();
}

static bool is_space(char c) { return c == ' ' || c == '\t'; }
static bool is_alpha(char c) { return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'); }
static bool is_digit(char c) { return c >= '0' && c <= '9'; }
static char to_lower(char c) { return (c >= 'A' && c <= 'Z') ? c + 32 : c; }

size_t HttpParser::parse(const char* data, size_t len) {
    size_t consumed = 0;

    for (size_t i = 0; i < len && !complete_; i++) {
        char c = data[i];
        consumed++;

        switch (state_) {
        case REQ_METHOD:
            if (is_alpha(c)) {
                req_.method += c;
            } else if (c == ' ') {
                state_ = REQ_SPACE_BEFORE_URL;
            }
            break;

        case REQ_SPACE_BEFORE_URL:
            if (c == ' ') break;
            state_ = REQ_URL;
            req_.path += c;
            break;

        case REQ_URL:
            if (c == ' ') {
                state_ = REQ_SPACE_BEFORE_VER;
            } else {
                req_.path += c;
            }
            break;

        case REQ_SPACE_BEFORE_VER:
            if (c == ' ') break;
            state_ = REQ_VERSION;
            req_.version += c;
            break;

        case REQ_VERSION:
            if (c == '\r') {
                state_ = REQ_CR;
            } else {
                req_.version += c;
            }
            break;

        case REQ_CR:
            if (c == '\n') {
                state_ = HEADER_KEY;
            }
            break;

        case HEADER_KEY:
            if (c == '\r') {
                state_ = HEADER_END_CR;
            } else if (c == ':') {
                state_ = HEADER_SPACE_BEFORE_VAL;
            } else {
                cur_key_ += to_lower(c);
            }
            break;

        case HEADER_SPACE_BEFORE_VAL:
            if (c == ' ') break;
            state_ = HEADER_VAL;
            cur_val_ += c;
            break;

        case HEADER_VAL:
            if (c == '\r') {
                state_ = HEADER_CR;
            } else {
                cur_val_ += c;
            }
            break;

        case HEADER_CR:
            if (c == '\n') {
                req_.headers[cur_key_] = cur_val_;
                cur_key_.clear();
                cur_val_.clear();
                state_ = HEADER_KEY;
            }
            break;

        case HEADER_END_CR:
            if (c == '\n') {
                // Headers complete, check for body
                auto it = req_.headers.find("content-length");
                if (it != req_.headers.end()) {
                    content_length_ = std::stoul(it->second);
                    if (content_length_ > 0) {
                        state_ = BODY;
                    } else {
                        state_ = DONE;
                        complete_ = true;
                    }
                } else {
                    state_ = DONE;
                    complete_ = true;
                }
            }
            break;

        case BODY: {
            // Remaining data is body
            size_t remaining = len - i;
            size_t need = content_length_ - body_read_;
            size_t take = (remaining < need) ? remaining : need;

            req_.body.append(data + i, take);
            body_read_ += take;
            i += take - 1;  // -1 because loop will increment
            consumed += take - 1;

            if (body_read_ >= content_length_) {
                state_ = DONE;
                complete_ = true;
            }
            break;
        }

        case DONE:
            break;
        }
    }

    if (complete_ && callback_) {
        callback_(req_);
    }

    return consumed;
}

} // namespace ylmz
