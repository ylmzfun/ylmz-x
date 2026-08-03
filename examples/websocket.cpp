#include <ylmz/ylmz.h>
#include <iostream>
#include <set>

int main() {
    ylmz::App app;

    app.Use(ylmz::Logger());

    // Serve a simple HTML page for testing WebSocket
    app.GET("/", [](ylmz::Context* ctx) {
        ctx->HTML(200, R"HTML(<!DOCTYPE html>
<html>
<head><title>ylmz WebSocket Chat</title></head>
<body>
    <h1>ylmz WebSocket Echo</h1>
    <input id="msg" type="text" placeholder="Type a message..." />
    <button onclick="send()">Send</button>
    <pre id="log"></pre>
    <script>
        var ws = new WebSocket('ws://' + location.host + '/ws');
        ws.onmessage = function(e) {
            document.getElementById('log').textContent += 'Server: ' + e.data + '\n';
        };
        ws.onopen = function() {
            document.getElementById('log').textContent += 'Connected!\n';
        };
        function send() {
            var input = document.getElementById('msg');
            ws.send(input.value);
            document.getElementById('log').textContent += 'You: ' + input.value + '\n';
            input.value = '';
        }
        document.getElementById('msg').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') send();
        });
    </script>
</body>
</html>)HTML");
    });

    // WebSocket echo server
    app.WS("/ws", [](ylmz::WSConn* ws) {
        std::cout << "[WS] New connection" << std::endl;

        ws->OnMessage([](ylmz::WSConn* conn, const std::string& msg) {
            std::cout << "[WS] Received: " << msg << std::endl;
            conn->Send("Echo: " + msg);
        });

        ws->OnClose([](ylmz::WSConn*) {
            std::cout << "[WS] Connection closed" << std::endl;
        });
    });

    app.Run(":8080");
    return 0;
}
