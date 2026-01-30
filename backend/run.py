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
    
    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║           🚀 Causal Finance API Server                       ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Environment: {config_name:<44} ║
    ║  Debug Mode:  {str(debug):<44} ║
    ║  URL:         http://localhost:{port}/api{' ' * (38 - len(str(port)))}║
    ║  Health:      http://localhost:{port}/api/health{' ' * (31 - len(str(port)))}║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
