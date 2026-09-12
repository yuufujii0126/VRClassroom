"""
録音ファイルを受け取って data/ に保存する小さなサーバ。

Usage:
    python server.py [--port 8000]

エンドポイント:
    GET  /              … recorder.html を表示
    GET  /<file>        … 静的ファイル配信
    POST /upload        … 音声 + メタデータJSONを受け取って data/ に保存
"""
import argparse
import cgi
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.lstrip("/") or "recorder.html"
        # 簡易セキュリティ: 親ディレクトリへの逃避を防ぐ
        target = (BASE_DIR / path).resolve()
        if not str(target).startswith(str(BASE_DIR)):
            self.send_error(403)
            return
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return

        ctype_map = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript",
            ".css": "text/css",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
        }
        ctype = ctype_map.get(target.suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/upload":
            self.send_error(404)
            return

        ctype = self.headers.get("Content-Type", "")
        if not ctype.startswith("multipart/form-data"):
            self.send_error(400, "multipart/form-data required")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": ctype},
        )

        session_id = form.getfirst("sessionId", "session").strip() or "session"
        session_id = "".join(c for c in session_id if c.isalnum() or c in "_-")

        saved = []

        audio_field = form["audio"] if "audio" in form else None
        if audio_field is not None and audio_field.file:
            ext = ".webm"
            audio_path = DATA_DIR / f"{session_id}{ext}"
            audio_path = self._unique_path(audio_path)
            with audio_path.open("wb") as f:
                while True:
                    chunk = audio_field.file.read(1024 * 64)
                    if not chunk:
                        break
                    f.write(chunk)
            saved.append(audio_path.name)

        meta_raw = form.getfirst("meta", "")
        if meta_raw:
            meta_path = DATA_DIR / f"{audio_path.stem}.json"
            meta_path.write_text(meta_raw, encoding="utf-8")
            saved.append(meta_path.name)

        resp = {"ok": True, "saved": saved, "dir": str(DATA_DIR)}
        body = json.dumps(resp, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _unique_path(path: Path) -> Path:
        if not path.exists():
            return path
        stem, suffix = path.stem, path.suffix
        i = 2
        while True:
            cand = path.with_name(f"{stem}_{i}{suffix}")
            if not cand.exists():
                return cand
            i += 1

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"録音サーバ起動: http://localhost:{args.port}/recorder.html")
    print(f"保存先: {DATA_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
