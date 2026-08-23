"""Static file server for frontend/ that DISABLES browser caching.

Same as `python -m http.server 8080` but every response carries
Cache-Control: no-store, so a normal refresh (F5) always loads the
latest HTML/JS — no Ctrl+F5 required while developing.
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os

PORT = 8080
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "frontend")
os.chdir(FRONTEND_DIR)


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):
        print("[frontend]", self.address_string(), "-", fmt % args)


if __name__ == "__main__":
    print(f"FloodGuard frontend serving on http://localhost:{PORT} "
          "(no-cache mode)")
    ThreadingHTTPServer(("127.0.0.1", PORT), NoCacheHandler).serve_forever()
