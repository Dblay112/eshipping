#!/usr/bin/env bash
set -o errexit

echo "==> Checking for DATABASE_URL..."
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set!"
    echo "Cannot run migrations without database connection."
    exit 1
fi

echo "==> DATABASE_URL is set, proceeding with migrations..."

# Clear Python cache to ensure fresh settings load
echo "==> Clearing Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Force settings module for consistent behavior across environments
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-eshipping.settings}"

echo "==> Verifying Django DB config..."
python -c "
import django
from django.conf import settings

django.setup()
print(f'DATABASES ENGINE: {settings.DATABASES[\"default\"][\"ENGINE\"]}')
print(f'DATABASES HOST: {settings.DATABASES[\"default\"].get(\"HOST\", \"N/A\")}')
print(f'DATABASES NAME: {settings.DATABASES[\"default\"].get(\"NAME\", \"N/A\")}')
"

# Note: Do not print DATABASE_URL to logs (may contain credentials)


echo "==> Fixing migration history (sd_tracker -> operations)..."
python manage.py fix_migration_history || echo "WARNING: fix_migration_history failed or not needed"

echo "==> Running migrations..."
python manage.py migrate --no-input

echo "================================================================================"
echo "==> CHECKING FOR SUPERUSER..."
echo "================================================================================"
python manage.py ensure_superuser || echo "WARNING: ensure_superuser command failed"
echo "================================================================================"

echo "==> Clearing template cache..."
python -c "from django.core.cache import cache; cache.clear()" 2>/dev/null || true

echo "==> Starting Gunicorn..."
exec gunicorn eshipping.wsgi:application --bind 0.0.0.0:$PORT --timeout 120 --workers 3
