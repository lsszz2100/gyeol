#!/usr/bin/env bash
echo "=============================================================================="
echo "  결(GYEOL) - 한국어 AI 프레젠테이션 & 디자인 스튜디오"
echo "=============================================================================="

if ! command -v python3 &> /dev/null; then
    echo "[오류] python3 명령을 찾을 수 없습니다."
    exit 1
fi

echo "[*] 결(GYEOL) 로컬 서버 구동 중..."
echo "[*] 브라우저 접속 주소: http://127.0.0.1:9090"

# 기본 브라우저 실행 시도 (WSL / Linux)
if command -v cmd.exe &> /dev/null; then
    cmd.exe /c start http://127.0.0.1:9090 2>/dev/null &
elif command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:9090 2>/dev/null &
fi

python3 app.py
