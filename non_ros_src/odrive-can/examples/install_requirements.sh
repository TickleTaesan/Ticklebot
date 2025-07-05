#!/bin/bash

echo "페달-ODrive 제어에 필요한 패키지 설치 중..."

# Python 패키지 설치
pip3 install pyserial python-can coloredlogs

# can-utils 설치 (candump 등)
sudo apt update
sudo apt install -y can-utils

echo "설치 완료!"
echo ""
echo "다음 단계:"
echo "1. ESP32 연결"
echo "2. ODrive CAN 연결" 
echo "3. 실행 가이드 참조: RUN_PEDAL_CONTROL.md" 