---
title: Finanza Banking Platform
emoji: 🏦
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 8000
pinned: false
---

# Finanza Banking & Financial Services Platform

Enterprise-grade banking and treasury application built with FastAPI, SQLAlchemy, PostgreSQL, and modern banking operations dashboards.

## Architecture
- **Backend**: FastAPI (Python 3.11 ASGI)
- **Database**: PostgreSQL (Supabase / Neon / Nile)
- **Frontend**: Responsive banking portal & admin dashboards
- **Compliance & Security**: OFAC SDN screening, AML monitoring, multi-factor authentication

## Hugging Face Spaces Deployment
This Space is configured with `sdk: docker` listening on `app_port: 8000`.
To set production secrets (database credentials, admin keys), navigate to **Settings** -> **Variables and Secrets** in the Space console.
