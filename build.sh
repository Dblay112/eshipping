#!/usr/bin/env bash
set -o errexit

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Installing Playwright browsers..."
playwright install chromium
playwright install-deps

echo "==> Collecting static files..."
# Set a dummy DATABASE_URL for collectstatic if not already set
# This prevents Django from caching SQLite config during build
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not set during build, using dummy PostgreSQL URL for collectstatic"
    export DATABASE_URL="postgresql://dummy:dummy@localhost:5432/dummy"
fi
python manage.py collectstatic --no-input

echo "==> Build completed successfully!"
echo "NOTE: Database operations will run during deployment phase"
