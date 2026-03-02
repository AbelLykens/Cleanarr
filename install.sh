#!/usr/bin/env bash
set -euo pipefail

echo "=== Opruimarr installer (Debian 13) ==="

# Install system dependencies
echo "Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip

# Create venv
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --quiet -r requirements.txt

# Set up .env if missing
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example — edit it with your API keys before running."
fi

# Run migrations
echo "Running database migrations..."
python manage.py migrate --run-syncdb

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys and settings"
echo "  2. Start the server:"
echo "     source venv/bin/activate"
echo "     python manage.py runserver 0.0.0.0:8000"
echo ""
echo "  3. (Optional) Run an initial library sync:"
echo "     python manage.py sync_library"
