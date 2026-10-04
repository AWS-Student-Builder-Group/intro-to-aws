#!/usr/bin/env python3
"""Serve the frontend locally at http://localhost:8000 (no dependencies).

The port matters: the S3 bucket CORS config allows this exact origin.

    python3 scripts/serve.py [--port 8000] [--no-browser]
"""
import argparse
import functools
import http.server
import threading
import webbrowser
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    """Disable caching so edits to config.js show up on a plain refresh."""

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    handler = functools.partial(NoCacheHandler, directory=str(FRONTEND_DIR))
    # Bind to localhost only so the dev server isn't exposed on the network.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler)

    url = f"http://localhost:{args.port}"
    print(f"Serving {FRONTEND_DIR} at {url} (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
