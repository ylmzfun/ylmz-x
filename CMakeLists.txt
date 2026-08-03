cmake_minimum_required(VERSION 3.14)
project(ylmz VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Platform detection
if(APPLE)
    add_definitions(-DYLMZ_PLATFORM_MACOS)
elseif(UNIX)
    add_definitions(-DYLMZ_PLATFORM_LINUX)
endif()

# nlohmann/json via FetchContent
include(FetchContent)
FetchContent_Declare(
    json
    URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)
FetchContent_MakeAvailable(json)

# Framework library
set(YLMZ_SOURCES
    src/event_loop.cpp
    src/http_parser.cpp
    src/router.cpp
    src/context.cpp
    src/middleware.cpp
    src/ws.cpp
    src/tcp.cpp
    src/app.cpp
)

set(YLMZ_HEADERS
    include/ylmz/ylmz.h
    include/ylmz/event_loop.h
    include/ylmz/http_parser.h
    include/ylmz/router.h
    include/ylmz/context.h
    include/ylmz/middleware.h
    include/ylmz/ws.h
    include/ylmz/tcp.h
    include/ylmz/app.h
)

add_library(ylmz STATIC ${YLMZ_SOURCES} ${YLMZ_HEADERS})
target_include_directories(ylmz PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_link_libraries(ylmz PUBLIC nlohmann_json::nlohmann_json)

# Examples
add_executable(example_hello examples/hello.cpp)
target_link_libraries(example_hello ylmz)

add_executable(example_rest examples/rest_api.cpp)
target_link_libraries(example_rest ylmz)

add_executable(example_ws examples/websocket.cpp)
target_link_libraries(example_ws ylmz)

add_executable(example_tcp examples/tcp_echo.cpp)
target_link_libraries(example_tcp ylmz)

# Tests
enable_testing()
add_executable(test_router tests/test_router.cpp)
target_link_libraries(test_router ylmz)
add_test(NAME test_router COMMAND test_router)
