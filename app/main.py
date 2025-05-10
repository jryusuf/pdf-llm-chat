from fastapi import FastAPI

# Import routers from feature modules
# from .account import router as account_router
# from .pdf import router as pdf_router
# from .chat import router as chat_router

app = FastAPI()


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"Hello": "World"}


# Include feature routers
# app.include_router(account_router, prefix="/account", tags=["account"])
# app.include_router(pdf_router, prefix="/pdf", tags=["pdf"])
# app.include_router(chat_router, prefix="/chat", tags=["chat"])

# You can run this app using `uvicorn app.main:app --reload`
