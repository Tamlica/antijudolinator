import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.db import SessionLocal, init_db
from app.classifier.store import seed_if_empty
from app.routes import admin, dashboard, overlay, webhook


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    session = SessionLocal()
    try:
        seed_if_empty(session)
    finally:
        session.close()
    yield


SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY")
if not SESSION_SECRET_KEY:
    raise RuntimeError("SESSION_SECRET_KEY must be set (see .env.example)")

app = FastAPI(title="antijudolinator", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(webhook.router)
app.include_router(overlay.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
