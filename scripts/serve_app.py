"""Serve the local design preview and its Excel export endpoint."""

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from generate_excel import generate_excel


ROOT = Path(__file__).resolve().parents[1]
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
MAX_REQUEST = 2 * 1024 * 1024


class AppHandler(SimpleHTTPRequestHandler):
    def list_directory(self, path):
        self.send_error(404)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        super().end_headers()

    def send_body(self, status, mime, content):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(content)

    def error_json(self, status, message):
        self.send_body(status, 'application/json', json.dumps({'error': message}).encode())

    def do_GET(self):
        if self.path == '/api/demo':
            self.send_body(200, 'application/json', (ROOT / 'tests' / 'demo_records.json').read_bytes())
            return
        super().do_GET()

    def do_POST(self):
        if self.path != '/api/export':
            self.error_json(404, 'Unknown endpoint.')
            return
        if self.headers.get_content_type() != 'application/json':
            self.error_json(415, 'Send the project as JSON.')
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_REQUEST:
                self.error_json(413, 'Project exceeds the export size limit or is empty.')
                return
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict) or not isinstance(data.get('project'), dict) or type(data.get('final')) is not bool:
                raise ValueError('Provide a project object and a draft or final export selection.')
            workbook = generate_excel(data['project'], final=data['final'])
        except (ValueError, ArithmeticError, TypeError, KeyError, AttributeError) as error:
            self.error_json(400, str(error))
            return
        self.send_body(200, XLSX, workbook)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    options = parser.parse_args()
    handler = partial(AppHandler, directory=ROOT / 'web')
    with ThreadingHTTPServer(('127.0.0.1', options.port), handler) as server:
        print(f'Preview at http://127.0.0.1:{server.server_port}/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
