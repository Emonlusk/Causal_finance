"""
Development Server Runner
=========================
Use this for local development only.
For production, use: gunicorn wsgi:app
"""

import os
from app import create_app

# Get config from environment or default to development
config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    # Development server settings
    debug = config_name == 'development'
    port = int(os.getenv('PORT', 5000))
    
    banner = f"""
    Causal Finance API Server
    -------------------------
    Environment: {config_name}
    Debug Mode:  {debug}
    URL:         http://localhost:{port}/api
    Health:      http://localhost:{port}/api/health
    """
    # Windows consoles may use cp1252; never let the banner kill the server
    try:
        print(banner)
    except UnicodeEncodeError:
        print(banner.encode('ascii', 'ignore').decode())

    app.run(host='0.0.0.0', port=port, debug=debug)
