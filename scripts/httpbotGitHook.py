from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def _handle(self):
        try:
            subprocess.check_call(['./launch.sh'], cwd='/root/recommendation/flask_recommendation', shell=True)
        finally:
            self.send_response_only(200)
            self.end_headers()
            self.finish()
            self.connection.close()  

if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 27182), Handler).serve_forever()


