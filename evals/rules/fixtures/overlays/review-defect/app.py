from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from hello import greet

PORT = 8008


class GreetingPage(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        name = query.get("name", ["world"])[1]
        body = f"<!doctype html><title>Greeter</title><h1>{greet(name)}</h1>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), GreetingPage).serve_forever()
