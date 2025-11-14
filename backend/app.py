from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lifespan import lifespan
from routes import api as api_router
from routes import ui as ui_router

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router.router)
app.include_router(ui_router.router)