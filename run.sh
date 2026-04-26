#!/bin/bash
set -e

echo "🚀 Evolution Lab 3D — build + run"

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate

pip install --upgrade pip
pip install neat-python fastapi uvicorn[standard] python-multipart httpx

cd frontend
npm install
npm run build
cd ..

echo "🌍 http://localhost:3030"
python main.py
