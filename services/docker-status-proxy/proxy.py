"""Expose only the Docker container list on an isolated, unpublished network."""
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import socket

MAX_RESPONSE = 2 * 1024 * 1024
FIELDS = ("Id", "Names", "Status", "Image", "State")


class DockerConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect("/var/run/docker.sock")


def container_list():
    connection = DockerConnection("localhost", timeout=5)
    try:
        connection.request("GET", "/containers/json?all=1")
        response = connection.getresponse()
        raw = response.read(MAX_RESPONSE + 1)
        if response.status != 200 or len(raw) > MAX_RESPONSE:
            raise ValueError("Docker response unavailable")
        items = json.loads(raw)
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise ValueError("Invalid Docker response")
        return [{key: item[key] for key in FIELDS if key in item} for item in items]
    finally:
        connection.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not log request headers, query strings or backend data.

    def reply(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        raw_path = self.requestline.split()[1]
        if raw_path != self.path or self.path not in ("/containers/json", "/containers/json?all=1"):
            return self.deny()
        try:
            payload = container_list()
        except (OSError, ValueError, http.client.HTTPException):
            return self.reply(503, {"error": "Docker status unavailable"})
        self.reply(200, payload)

    def deny(self):
        self.reply(403, {"error": "Only GET /containers/json is allowed"})

    do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = do_CONNECT = do_TRACE = deny


class Server(HTTPServer):
    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(3)
        return connection, address


if __name__ == "__main__":
    Server(("0.0.0.0", 2375), Handler).serve_forever()
