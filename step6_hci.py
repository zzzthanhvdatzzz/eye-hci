"""Local Eye HCI dashboard. Run python step6_hci.py --help."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import webbrowser
from eye_hci.runtime import Runtime

WEB = Path(__file__).resolve().parent / 'web'

def make_handler(runtime):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, data, kind='application/json; charset=utf-8'):
            self.send_response(code)
            self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.valid_host():
                self.send(403,b'{}')
                return
            path = self.path.split('?')[0]
            if path == '/api/state':
                self.send(200,json.dumps(runtime.snapshot()).encode())
            elif path == '/api/wallpaper':
                try:
                    from eye_hci.desktop import wallpaper_image
                    self.send(200,wallpaper_image(),'image/png')
                except Exception as exc:
                    self.send(404,json.dumps({'error':str(exc)}).encode())
            elif path == '/api/frame':
                with runtime.lock:
                    frame = runtime.jpeg
                self.send(200 if frame else 204,frame or b'','image/jpeg')
            elif path in ('/','/app.js','/style.css'):
                name = 'index.html' if path == '/' else path[1:]
                kind = {'index.html':'text/html; charset=utf-8', 'app.js':'text/javascript; charset=utf-8',
                        'style.css':'text/css; charset=utf-8'}[name]
                self.send(200,(WEB/name).read_bytes(),kind)
            else:
                self.send(404,b'{}')

        def do_POST(self):
            # Only local dashboard JavaScript can send control requests; no CORS.
            expected = f'http://127.0.0.1:{self.server.server_port}'
            if not self.valid_host() or self.headers.get('Origin') != expected or self.headers.get('X-Eye-HCI') != '1':
                self.send(403,b'{}')
                return
            if self.path != '/api/control':
                self.send(404,b'{}')
                return
            try:
                size = int(self.headers.get('Content-Length','0'))
                if not 0 < size < 2048:
                    raise ValueError('Yêu cầu không hợp lệ.')
                body = json.loads(self.rfile.read(size))
                runtime.command(body['action'],body.get('value'))
                self.send(200,b'{"ok":true}')
            except Exception as exc:
                self.send(400,json.dumps({'error':str(exc)}).encode())
    return Handler

def main():
    parser = argparse.ArgumentParser(description='Eye HCI • giao diện local, mặc định dry-run')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--camera',type=int,default=0)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--desktop',action='store_true',help='Mở cửa sổ desktop có chế độ nổi thu gọn')
    parser.add_argument('--real',action='store_true',help='Bật chế độ điều khiển thật, vẫn cần Tiếp tục trong giao diện')
    args = parser.parse_args()
    runtime = Runtime(args.camera)
    if args.real:
        runtime.command('real',True)
    try:
        server = ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(runtime))
    except OSError:
        if not args.desktop or args.port == 0:
            raise
        # Reuse the running local dashboard rather than compete for its camera.
        import urllib.request
        existing = f'http://127.0.0.1:{args.port}'
        with urllib.request.urlopen(existing+'/api/state',timeout=2) as response:
            state = json.load(response)
        if not isinstance(state,dict) or not {'status','profile','events'} <= state.keys():
            raise ValueError('Cổng đang được ứng dụng khác sử dụng. Chọn --port khác.')
        from eye_hci.desktop import launch
        launch(existing)
        return
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Eye HCI: {url}\nCtrl+C để thoát. Camera chỉ bật khi nhấn nút trong giao diện.')
    if not args.no_browser and not args.desktop:
        threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try:
        if args.desktop:
            from eye_hci.desktop import launch
            worker = threading.Thread(target=server.serve_forever,daemon=True)
            worker.start()
            try:
                launch(url)
            finally:
                server.shutdown()
                worker.join(timeout=3)
        else:
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.command('stop')
        if runtime.thread:
            runtime.thread.join(timeout=5)
        server.server_close()

if __name__ == '__main__':
    main()
