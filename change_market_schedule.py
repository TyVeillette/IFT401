from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os
import webbrowser


HOST = "127.0.0.1"
PORT = 8000


if __name__ == "__main__":

    # Serve files from the same directory as app.py
    project_directory = Path(__file__).resolve().parent
    os.chdir(project_directory)

    url = f"http://{HOST}:{PORT}/market_schedule.html"

    print("Stock Trading System")
    print(f"Running at: {url}")
    print("Press Ctrl+C to stop the server.")

    webbrowser.open(url)

    server = HTTPServer(
        (HOST, PORT),
        SimpleHTTPRequestHandler
    )

    server.serve_forever()
