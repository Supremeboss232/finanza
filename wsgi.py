import os
import sys

# Add application directory to sys.path
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Set defaults if not provided in environment
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{os.path.join(app_dir, 'finanza.db')}"

if not os.environ.get("ENVIRONMENT"):
    os.environ["ENVIRONMENT"] = "production"

if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "finanza-secure-random-secret-key-2026-production"

from a2wsgi import ASGIMiddleware
from main import app

# WSGI application callable for PythonAnywhere
application = ASGIMiddleware(app)
