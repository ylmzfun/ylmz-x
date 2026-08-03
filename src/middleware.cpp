#include "ylmz/middleware.h"
#include <iostream>
#include <chrono>
#include <ctime>
#include <iomanip>

namespace ylmz {

MiddlewareFunc Logger() {
    return [](Context* ctx) {
        auto start = std::chrono::steady_clock::now();

        // Call next middleware/handler
        ctx->Next();

        auto end = std::chrono::steady_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();

        // Format: [2024-01-01 12:00:00] GET /path 200 1234μs
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                      now.time_since_epoch()) % 1000;

        std::tm tm;
        localtime_r(&time_t, &tm);

        char time_buf[32];
        strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S", &tm);

        // We can't easily get status code after middleware chain,
        // but we can log basic info
        fprintf(stdout, "[%s.%03lld] %s %s %lldμs\n",
                time_buf, (long long)ms.count(),
                ctx->Method().c_str(), ctx->Path().c_str(),
                (long long)duration);
    };
}

MiddlewareFunc Recovery() {
    return [](Context* ctx) {
        try {
            ctx->Next();
        } catch (const std::exception& e) {
            fprintf(stderr, "[Recovery] panic: %s\n", e.what());
            ctx->JSON(500, {{"error", "Internal Server Error"}});
        } catch (...) {
            fprintf(stderr, "[Recovery] unknown panic\n");
            ctx->JSON(500, {{"error", "Internal Server Error"}});
        }
    };
}

MiddlewareFunc CORS(const std::string& allow_origin,
                    const std::string& allow_methods,
                    const std::string& allow_headers) {
    std::string origin = allow_origin;
    std::string methods = allow_methods;
    std::string headers = allow_headers;

    return [origin, methods, headers](Context* ctx) {
        ctx->SetHeader("Access-Control-Allow-Origin", origin);
        ctx->SetHeader("Access-Control-Allow-Methods", methods);
        ctx->SetHeader("Access-Control-Allow-Headers", headers);

        if (ctx->Method() == "OPTIONS") {
            ctx->String(204, "");
            return;
        }

        ctx->Next();
    };
}

} // namespace ylmz
