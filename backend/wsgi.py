"""
WSGI Entry Point for Production Deployment
==========================================
This file is the entry point for Gunicorn (production WSGI server).
Render, Heroku, and other PaaS platforms use this to start the app.

Usage:
  gunicorn wsgi:app --bind 0.0.0.0:$PORT
"""

import os
from app import create_app

# Always use production config when running via WSGI
config_name = os.getenv('FLASK_ENV', 'production')
app = create_app(config_name)

# This is what Gunicorn imports
if __name__ == '__main__':
    app.run()
