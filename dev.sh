#!/bin/bash
set -e

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install neat-python fastapi uvicorn[standard] python-multipart httpx

cd frontend
npm install
cd ..

echo "Backend:  http://localhost:3030"
echo "Frontend: http://localhost:5173"
python main.py &
BACK_PID=$!
cd frontend
npm run dev
kill $BACK_PID
