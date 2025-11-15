"""
Vercel Serverless Entry Point
This file exposes the Flask app to Vercel's Python runtime
"""

from app import app

# Vercel looks for either 'app' or 'handler'
# Export the Flask app instance
handler = app

# For local testing
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)