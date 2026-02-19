"""App-local schemas shim

Re-export project-level pydantic schemas so modules inside the `app`
package can use `from .schemas import ...`.

This mirrors the pattern used for `app.config` and keeps the single
source-of-truth for schemas at the project root (`schemas.py`).
"""
try:
    # Prefer importing the project's top-level schemas module
    from schemas import *  # noqa: F401,F403
    # If desired, you can also explicitly export names here, e.g.
    # from schemas import Token, TokenData, User, UserCreate, FormSubmissionCreate
except Exception:
    # Minimal fallbacks to avoid ImportError during certain tooling runs.
    from pydantic import BaseModel
    class _Fallback(BaseModel):
        pass

    Token = _Fallback
    TokenData = _Fallback
    User = _Fallback
    UserCreate = _Fallback
    FormSubmissionCreate = _Fallback

__all__ = [
    name for name in globals().keys() if not name.startswith("_")
]
