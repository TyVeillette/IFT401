from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os

HOST = "127.0.0.1"
PORT = 8000

if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)

    server = HTTPServer((HOST, PORT), SimpleHTTPRequestHandler)

    print(f"Open http://{HOST}:{PORT}/market_hours.html")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
