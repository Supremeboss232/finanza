# Procfile — for Heroku, Railway, Render, and other Procfile-compatible platforms
# Docs: https://devcenter.heroku.com/articles/procfile

# Web process: starts the FastAPI app
# $PORT is automatically set by the platform (Heroku/Railway/Render inject it)
web: uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2

# Release process: runs database migrations before each deploy
release: alembic upgrade head
