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


app = FastAPI(title="antijudolinator", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET_KEY", "dev-secret-change-me"),
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(webhook.router)
app.include_router(overlay.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
