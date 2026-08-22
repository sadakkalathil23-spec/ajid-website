#!/usr/bin/env python3
"""
AJID dev/admin server.

Serves the static site AND accepts saves from the admin panel:

  GET  /api/content       -> current content/site.json
  POST /api/content       -> overwrite content/site.json, then rebuild both pages
  POST /api/upload        -> save an uploaded image into assets/img/

Run:  python server.py           (defaults to port 3020)
"""
import json, base64, re, pathlib, sys, shutil, datetime

try:  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT     = pathlib.Path(__file__).parent.resolve()
CONTENT  = ROOT / "content" / "site.json"
BACKUPS  = ROOT / "content" / "backups"
IMG_DIR  = ROOT / "assets" / "img"
PORT     = int(sys.argv[1]) if len(sys.argv) > 1 else 3020

SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".svg"}
MAX_UPLOAD = 12 * 1024 * 1024   # 12 MB


def rebuild():
    """Regenerate index.html and ar/index.html from the saved JSON."""
    import importlib
    sys.path.insert(0, str(ROOT))
    import build
    importlib.reload(build)
    build.main()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    # ---- helpers -------------------------------------------------------
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD:
            raise ValueError("payload too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def end_headers(self):
        # keep the dev loop honest — never serve a stale page while editing
        if self.path.endswith((".html", ".css", ".js", ".json")) or self.path.endswith("/"):
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()

    # ---- routes --------------------------------------------------------
    def do_GET(self):
        if self.path.split("?")[0] == "/api/content":
            return self._json(json.loads(CONTENT.read_text(encoding="utf8")))
        return super().do_GET()

    def do_POST(self):
        route = self.path.split("?")[0]
        try:
            if route == "/api/content":
                data = self._body()
                if not isinstance(data, dict) or "theme" not in data or "en" not in data:
                    return self._json({"ok": False, "error": "malformed content"}, 400)

                # keep a timestamped backup before every overwrite
                BACKUPS.mkdir(parents=True, exist_ok=True)
                stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                if CONTENT.exists():
                    shutil.copy2(CONTENT, BACKUPS / f"site-{stamp}.json")

                CONTENT.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8")
                rebuild()
                return self._json({"ok": True, "backup": f"site-{stamp}.json"})

            if route == "/api/upload":
                d = self._body()
                name = SAFE_NAME.sub("_", pathlib.Path(d.get("name", "")).name)
                ext = pathlib.Path(name).suffix.lower()
                if ext not in ALLOWED_EXT:
                    return self._json({"ok": False, "error": f"extension {ext} not allowed"}, 400)
                raw = base64.b64decode(d.get("data", "").split(",", 1)[-1])
                if len(raw) > MAX_UPLOAD:
                    return self._json({"ok": False, "error": "file too large"}, 400)
                IMG_DIR.mkdir(parents=True, exist_ok=True)
                target = IMG_DIR / name
                # never clobber an existing asset silently
                stem, n = target.stem, 1
                while target.exists():
                    target = IMG_DIR / f"{stem}-{n}{ext}"
                    n += 1
                target.write_bytes(raw)
                return self._json({"ok": True, "path": f"/assets/img/{target.name}"})

            return self._json({"ok": False, "error": "unknown route"}, 404)

        except Exception as exc:                      # noqa: BLE001 - surface to the panel
            return self._json({"ok": False, "error": str(exc)}, 500)

    def log_message(self, fmt, *args):
        if "/api/" in (self.path or ""):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    rebuild()
    print(f"AJID site   ->  http://localhost:{PORT}/")
    print(f"Admin panel ->  http://localhost:{PORT}/admin.html")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
