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
import base64
import json
import os
import pickle
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import aggregate
import sources

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw-data")

_AUTH_USER = os.environ.get("AUTH_USERNAME", "")
_AUTH_PASS = os.environ.get("AUTH_PASSWORD", "")
_AUTH_ENABLED = bool(_AUTH_USER and _AUTH_PASS)
_AUTH_CRED = f"{_AUTH_USER}:{_AUTH_PASS}".encode("utf-8") if _AUTH_ENABLED else b""
_AUTH_B64 = base64.b64encode(_AUTH_CRED).decode("ascii") if _AUTH_ENABLED else ""

_src = sources.from_env(RAW)
SOURCE = _src[0]
SOURCE_KIND = _src[1]
ACTIVITY_SOURCE = _src[2] if len(_src) > 2 else None

CACHE_DIR = "/tmp/ugame-dashboard-cache"
CACHE_FILE = os.path.join(CACHE_DIR, "state.pkl")
PID_FILE = os.path.join(CACHE_DIR, ".pid")


def _cache_valid():
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            return int(f.read().strip()) == os.getpid()
    except (ValueError, OSError):
        return False


def _init_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not _cache_valid():
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))


def _load_state():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "rb") as f:
                return pickle.load(f)
        except (pickle.UnpicklingError, EOFError, OSError):
            pass
    return None


def _save_state(state):
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(state, f, pickle.HIGHEST_PROTOCOL)


def _build_file_map(source):
    """從 source.signature() 建立 {filename: (size, mtime, oss_key)} 映射。"""
    fm = {}
    for item in source.signature():
        key = item[0]
        size = item[1]
        mtime = item[2] if len(item) > 2 else 0
        name = key.split("/")[-1]
        fm[name] = (size, mtime, key)
    return fm


def get_summary():
    _init_cache()

    curr_files = _build_file_map(SOURCE)
    state = _load_state()

    # 快取命中 → 直接回傳
    cached_files = state.get("files") if state else None
    if cached_files and cached_files == curr_files:
        return state["data"]

    # 找出新增/變更的檔案 → 只下載這些
    new_keys = None
    if cached_files and state.get("intermediate"):
        new_keys = set()
        for name, (size, mtime, oss_key) in curr_files.items():
            prev = cached_files.get(name)
            if prev is None or prev[:2] != (size, mtime):
                new_keys.add(oss_key)
        if not new_keys:
            new_keys = None  # 無新檔 → 全量（活動源可能變更）

    if state and state.get("intermediate"):
        inter = state["intermediate"]
        data, inter = aggregate.aggregate(SOURCE, ACTIVITY_SOURCE, base=inter, only_keys=new_keys)
    else:
        data, inter = aggregate.aggregate(SOURCE, ACTIVITY_SOURCE)

    _save_state({"files": curr_files, "data": data, "intermediate": inter})
    return data


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if _AUTH_ENABLED:
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Basic ") or auth[6:] != _AUTH_B64:
                self.send_response(401)
                self.send_header("WWW-Authenticate",
                                 'Basic realm="U.Game Dashboard", charset="UTF-8"')
                self.end_headers()
                self.wfile.write(b"401 Unauthorized")
                return
        path = self.path.split("?", 1)[0]
        if path in ("/api/summary", "/api/summary/"):
            try:
                payload = json.dumps(get_summary(), ensure_ascii=False).encode("utf-8")
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
