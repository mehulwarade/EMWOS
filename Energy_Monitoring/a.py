#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class RequestHandler(BaseHTTPRequestHandler):
    def _send_response(self, message):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(message.encode())

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        json_data = json.loads(post_data.decode('utf-8'))

        value = json_data.get('value', None)
        if value is not None:
            client_address = self.client_address[0]
            print(f"Received value {value} from IP address {client_address}")
            self._send_response(f"Received value {value} from IP address {client_address}")
        else:
            self._send_response("Invalid JSON format")

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8443):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting server on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
