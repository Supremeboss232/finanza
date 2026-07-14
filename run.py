import uvicorn
import os

# Load .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely on system env vars

if __name__ == "__main__":
    # Use 0.0.0.0 to bind on all interfaces (required for EC2/VPS/Docker deployments)
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("ENVIRONMENT", "development") == "development"
    uvicorn.run("main:app", host=host, port=port, reload=reload)