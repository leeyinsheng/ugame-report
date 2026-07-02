#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
U.Game 运营数据看板 —— 本地服务器

用法：
    python3 server.py            # 默认 http://localhost:8000
    python3 server.py 8080       # 指定端口

工作方式：
    · 把后台导出的原始 CSV 放进  Dashboard/raw-data/
    · 浏览器打开看板，前端请求 /api/summary
    · 服务器实时扫描 raw-data/ 聚合成每日指标返回（按文件 mtime 缓存，
      只有新增 / 替换文件时才重算）—— 上传后刷新页面即时生效。
仅依赖 Python 标准库。
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import aggregate
import sources

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw-data")

SOURCE, SOURCE_KIND = sources.from_env(RAW)

_cache = {"sig": None, "data": None}


def get_summary():
    sig = SOURCE.signature()
    if sig != _cache["sig"]:
        _cache["data"] = aggregate.aggregate(SOURCE)
        _cache["sig"] = sig
    return _cache["data"]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/api/summary", "/api/summary/"):
            try:
                payload = json.dumps(get_summary(), ensure_ascii=False).encode("utf-8")
                self._send(200, payload, "application/json; charset=utf-8")
            except Exception as e:  # noqa: BLE001
                self._send(500, json.dumps({"error": str(e)}).encode("utf-8"),
                           "application/json; charset=utf-8")
            return
        if path.startswith("/api/reconcile"):
            try:
                params = parse_qs(urlparse(self.path).query)
                member_id = (params.get("member_id") or [""])[0]
                if not member_id:
                    self._send(400, json.dumps({"error": "missing member_id"}).encode("utf-8"),
                               "application/json; charset=utf-8")
                    return
                import reconcile as rec_mod
                r = rec_mod.Reconciliator(SOURCE, member_id)
                result = r.run()
                payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self._send(200, payload, "application/json; charset=utf-8")
            except Exception as e:  # noqa: BLE001
                self._send(500, json.dumps({"error": str(e)}).encode("utf-8"),
                           "application/json; charset=utf-8")
            return
        if path in ("/", "/index.html"):
            return self._file("index.html", "text/html; charset=utf-8")
        # 静态文件（限定在 BASE 内，禁止越界）
        rel = os.path.normpath(path.lstrip("/"))
        if rel.startswith("..") or os.path.isabs(rel):
            return self._send(403, b"forbidden", "text/plain")
        return self._file(rel, None)

    def _file(self, rel, ctype):
        full = os.path.join(BASE, rel)
        if not os.path.isfile(full):
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        if ctype is None:
            ext = os.path.splitext(full)[1].lower()
            ctype = {".html": "text/html; charset=utf-8", ".js": "text/javascript",
                     ".css": "text/css", ".json": "application/json"}.get(ext,
                     "application/octet-stream")
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype)

    def log_message(self, *a):   # 静默普通日志
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    try:
        sys.stdout.reconfigure(line_buffering=True)  # systemd/journal 下日志即时可见
    except Exception:  # noqa: BLE001
        pass
    if SOURCE_KIND != "OSS":
        os.makedirs(RAW, exist_ok=True)
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"U.Game 看板已启动：http://localhost:{port}")
    if SOURCE_KIND == "OSS":
        print(f"数据源：OSS  bucket={os.environ.get('OSS_BUCKET')}  prefix={os.environ.get('OSS_PREFIX', 'raw-data/')}")
        print("（把后台导出 CSV 上传到该 OSS 前缀下，刷新页面即时更新；Ctrl+C 停止）")
    else:
        print(f"数据源：本地目录 {RAW}")
        print("（把后台导出 CSV 放进该目录，刷新页面即时更新；Ctrl+C 停止）")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
