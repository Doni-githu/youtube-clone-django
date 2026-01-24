#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies (modify as needed for pip, poetry, etc.)
pip install -r requirements.txt

# Convert static asset files
python manage.py collectstatic

# Apply database migrations
python manage.py migrate