#!/bin/bash
# 双击启动 U.Game 运营数据看板（macOS）
cd "$(dirname "$0")"
echo "正在启动 U.Game 运营数据看板…"
# 取本机局域网 IP，方便手机访问
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo "本机访问：     http://localhost:8000"
[ -n "$IP" ] && echo "手机访问(同WiFi)：http://$IP:8000"
# 自动用默认浏览器打开
( sleep 1.2; open "http://localhost:8000" ) &
python3 server.py 8000
