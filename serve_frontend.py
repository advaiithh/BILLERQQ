import http.server
import socketserver
import os
from urllib.parse import unquote, urlparse

PORT = 3000
ROOT = os.path.join(os.path.dirname(__file__), 'build')

class SpaHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = urlparse(path).path
        path = unquote(path)
        if path.startswith('/'):
            path = path[1:]
        full_path = os.path.join(ROOT, path)
        if os.path.isdir(full_path):
            full_path = os.path.join(full_path, 'index.html')
        if not os.path.exists(full_path):
            return os.path.join(ROOT, 'index.html')
        return full_path

    def log_message(self, format, *args):
        print(format % args)

if __name__ == '__main__':
    os.chdir(ROOT)
    handler = SpaHandler
    with socketserver.TCPServer(('127.0.0.1', PORT), handler) as httpd:
        print(f'Serving frontend at http://127.0.0.1:{PORT}')
        httpd.serve_forever()
