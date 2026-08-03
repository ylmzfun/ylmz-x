CXX := clang++
CXXFLAGS := -std=c++17 -Wall -Wextra -O2 -g
INCLUDES := -I include
LDFLAGS :=

# Platform detection
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    CXXFLAGS += -DYLMZ_PLATFORM_MACOS
endif
ifeq ($(UNAME_S),Linux)
    CXXFLAGS += -DYLMZ_PLATFORM_LINUX
endif

SRC_DIR := src
BUILD_DIR := build/obj

SRCS := $(wildcard $(SRC_DIR)/*.cpp)
OBJS := $(SRCS:$(SRC_DIR)/%.cpp=$(BUILD_DIR)/%.o)

EXAMPLES := example_hello example_rest example_ws example_tcp
TEST := test_router

.PHONY: all clean examples test

all: examples test

# Framework library
libylmz.a: $(OBJS)
	ar rcs $@ $^

# Compile source files
$(BUILD_DIR)/%.o: $(SRC_DIR)/%.cpp
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

# Examples
example_hello: examples/hello.cpp libylmz.a
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -L. -lylmz -o $@

example_rest: examples/rest_api.cpp libylmz.a
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -L. -lylmz -o $@

example_ws: examples/websocket.cpp libylmz.a
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -L. -lylmz -o $@

example_tcp: examples/tcp_echo.cpp libylmz.a
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -L. -lylmz -o $@

test_router: tests/test_router.cpp libylmz.a
	$(CXX) $(CXXFLAGS) $(INCLUDES) $< -L. -lylmz -o $@

examples: $(EXAMPLES)

test: $(TEST)
	./test_router

clean:
	rm -rf build libylmz.a $(EXAMPLES) $(TEST)
