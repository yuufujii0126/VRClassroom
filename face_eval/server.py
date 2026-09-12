"""
録画ファイル + 検出ログ JSON を data/ に保存するアップロードサーバ。

Usage:
    python server.py [--port 8001]
"""
import argparse
import cgi
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Handler(BaseHTTPRequestHandler):
    CTYPE_MAP = {
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript",
        ".css": "text/css",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".webm": "video/webm",
        ".mp4": "video/mp4",
    }

    def _resolve(self):
        parsed = urlparse(self.path)
        if parsed.path == "/list":
            return ("list", parsed)
        raw_path = unquote(parsed.path).lstrip("/") or "recorder.html"
        target = (BASE_DIR / raw_path).resolve()
        if not str(target).startswith(str(BASE_DIR)):
            return ("forbidden", None)
        if not target.exists() or not target.is_file():
            return ("notfound", None)
        return ("file", target)

    def do_HEAD(self):
        kind, payload = self._resolve()
        if kind == "list":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            return
        if kind == "forbidden":
            self.send_error(403); return
        if kind == "notfound":
            self.send_error(404); return
        target = payload
        ctype = self.CTYPE_MAP.get(target.suffix, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(target.stat().st_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/list":
            qs = parse_qs(parsed.query)
            ext = qs.get("ext", ["json"])[0]
            files = sorted(p.name for p in DATA_DIR.glob(f"*.{ext}")
                           if not p.name.endswith(".annotation.json"))
            self._send_json({"files": files})
            return

        kind, target = self._resolve()
        if kind == "forbidden":
            self.send_error(403); return
        if kind == "notfound":
            self.send_error(404); return

        ctype = self.CTYPE_MAP.get(target.suffix, "application/octet-stream")
        file_size = target.stat().st_size

        # Range リクエスト対応（動画シーク用）
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            try:
                rng = range_header[len("bytes="):]
                start_s, end_s = rng.split("-", 1)
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else file_size - 1
                end = min(end, file_size - 1)
                if start > end or start >= file_size:
                    self.send_error(416); return
                with target.open("rb") as f:
                    f.seek(start)
                    body = f.read(end - start + 1)
                self.send_response(206)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            except ValueError:
                pass

        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/upload" and self.path != "/save_annotation":
            self.send_error(404)
            return

        ctype = self.headers.get("Content-Type", "")
        if not ctype.startswith("multipart/form-data") and not ctype.startswith("application/json"):
            self.send_error(400, "multipart or json required")
            return

        if self.path == "/save_annotation":
            return self._save_annotation()

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": ctype},
        )

        session_id = form.getfirst("sessionId", "session").strip() or "session"
        session_id = "".join(c for c in session_id if c.isalnum() or c in "_-")

        saved = []
        video_path = None
        for field_name in ("video", "audio"):
            if field_name in form and form[field_name].file:
                f = form[field_name]
                suffix = ".webm"
                if "mp4" in (f.type or ""):
                    suffix = ".mp4"
                video_path = self._unique_path(DATA_DIR / f"{session_id}{suffix}")
                with video_path.open("wb") as out:
                    while True:
                        chunk = f.file.read(1024 * 64)
                        if not chunk:
                            break
                        out.write(chunk)
                saved.append(video_path.name)
                break

        meta_raw = form.getfirst("meta", "")
        if meta_raw:
            stem = video_path.stem if video_path else session_id
            meta_path = self._unique_path(DATA_DIR / f"{stem}.json")
            meta_path.write_text(meta_raw, encoding="utf-8")
            saved.append(meta_path.name)

        resp = {"ok": True, "saved": saved, "dir": str(DATA_DIR)}
        self._send_json(resp)

    def _save_annotation(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body)
        session_id = payload.get("sessionId", "session")
        session_id = "".join(c for c in session_id if c.isalnum() or c in "_-")
        out = DATA_DIR / f"{session_id}.annotation.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._send_json({"ok": True, "saved": out.name})

    def _send_json(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
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
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"face_eval サーバ起動: http://localhost:{args.port}/recorder.html")
    print(f"アノテーション: http://localhost:{args.port}/annotate.html")
    print(f"保存先: {DATA_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
