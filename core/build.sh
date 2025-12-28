#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Convert static files (CSS/JS)
python manage.py collectstatic --no-input

# Update the database
python manage.py migrate