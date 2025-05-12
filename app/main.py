from fastapi import FastAPI

from app.core.dependencies import async_engine, Base

from app.account.controller.routers import router as account_router
from app.pdf.controller.routers import router as pdf_router
from app.chat.controllers.routers import router as chat_router

import sys
from loguru import logger


from app.core.database_mongo import (
    connect_to_mongo,
    close_mongo_connection,
)

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"Hello": "World"}


app.include_router(account_router, tags=["account"])
app.include_router(pdf_router, tags=["pdf"])
app.include_router(chat_router, tags=["chat"])
