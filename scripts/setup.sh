#!/usr/bin/env bash
set -e

echo ">>> Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ">>> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo ">>> .env created. Please edit it with your BOT_TOKEN and LLM_API_KEY"
fi

mkdir -p data logs generated

echo ">>> Setup complete!"
echo "1. Edit .env"
echo "2. Run: source venv/bin/activate && python main.py"
