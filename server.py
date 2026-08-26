#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
27秋招本地服务（静态文件 + API 刷新端点）
- 静态托管整个 27秋招 目录
- GET /api/refresh-deepseek : 重新抓取 DeepSeek 余额，刷新 deepseek_usage.js
- GET /api/refresh-mail      : 重新读取邮件，刷新 mail_events.js
用法: python server.py [端口]   （默认 8000）
"""
import http.server, socketserver, subprocess, json, os, sys, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
PY = sys.executable

def run_script(name):
    """运行 fetch 脚本，返回 (ok, output)"""
    try:
        r = subprocess.run(
            [PY, os.path.join(ROOT, name)],
            capture_output=True, text=True, timeout=120, cwd=ROOT,
            encoding='utf-8', errors='replace',
        )
        return r.returncode == 0, (r.stdout or '')[-500:] + (('\n[err] ' + r.stderr[-300:]) if r.returncode != 0 else '')
    except subprocess.TimeoutExpired:
        return False, '脚本执行超时'
    except Exception as e:
        return False, str(e)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == '/api/refresh-deepseek':
            return self._api_refresh('fetch_deepseek.py')
        if path == '/api/refresh-mail':
            return self._api_refresh('read_mail.py')
        return super().do_GET()

    def _api_refresh(self, script):
        ok, out = run_script(script)
        body = json.dumps({'ok': ok, 'output': out}, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stdout.write('[%s] %s\n' % (self.log_date_time_string(), fmt % args))

if __name__ == '__main__':
    # 绑定 0.0.0.0 便于局域网分享
    with socketserver.TCPServer(('0.0.0.0', PORT), Handler) as httpd:
        print(f'Serving 27秋招 on http://0.0.0.0:{PORT}  (Ctrl+C 停止)')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n已停止')
