from fastapi import FastAPI

# Import database components
from .core.dependencies import async_engine, Base

# Import routers from feature modules
from .account.controller.routers import router as account_router
# from .pdf import router as pdf_router
# from .chat import router as chat_router

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    # Create database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"Hello": "World"}


# Include feature routers
app.include_router(account_router, prefix="/account", tags=["account"])
# app.include_router(pdf_router, prefix="/pdf", tags=["pdf"])
# app.include_router(chat_router, prefix="/chat", tags=["chat"])

# You can run this app using `uvicorn app.main:app --reload`
