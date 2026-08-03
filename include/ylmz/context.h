#pragma once

#include <string>
#include <map>
#include <vector>
#include <functional>
#include <sstream>
#include "json.hpp"

namespace ylmz {

using json = nlohmann::json;

class Context {
public:
    Context(int fd);
    ~Context() = default;

    // --- Request ---
    const std::string& Method() const;
    const std::string& Path() const;
    const std::string& Version() const;
    std::string GetHeader(const std::string& key) const;
    const std::map<std::string, std::string>& Headers() const;
    const std::string& Body() const;

    // Query parameter: ?key=value
    std::string Query(const std::string& key) const;

    // Path parameter: /user/:id
    std::string Param(const std::string& key) const;

    // Bind JSON body to a type
    template<typename T>
    T BindJSON() const {
        return json::parse(body_).get<T>();
    }

    // Get raw JSON body
    json GetJSON() const {
        if (body_.empty()) return json::object();
        return json::parse(body_);
    }

    // --- Response ---
    void SetStatus(int code);
    void SetHeader(const std::string& key, const std::string& value);

    // Write response body
    void String(int code, const std::string& s);
    void JSON(int code, const json& data);
    void HTML(int code, const std::string& html);

    // Send raw data
    void Data(int code, const std::string& content_type, const std::string& data);

    // --- Internal use ---
    void set_request(const struct HttpRequest& req);
    void set_params(std::map<std::string, std::string> params);
    void set_middlewares(std::vector<std::function<void(Context*)>>* mws);
    int fd() const { return fd_; }
    bool responded() const { return responded_; }

    // Middleware chain: call to proceed to the next middleware/handler
    void Next();

private:
    int fd_;
    std::string method_;
    std::string path_;
    std::string version_;
    std::map<std::string, std::string> headers_;
    std::string body_;
    std::string query_string_;

    std::map<std::string, std::string> params_;
    mutable std::map<std::string, std::string> query_cache_;

    int status_code_ = 200;
    std::map<std::string, std::string> resp_headers_;
    bool responded_ = false;

    std::vector<std::function<void(Context*)>>* middlewares_ = nullptr;
    size_t middleware_index_ = 0;

    void parse_query_string() const;
    void write_response(const std::string& content_type, const std::string& data);
};

} // namespace ylmz
