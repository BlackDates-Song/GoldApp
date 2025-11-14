from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from lifespan import lifespan
from routes import api as api_router

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router.router)

# 4. [v4.63] 挂载静态文件 (前端)
#    这必须在所有 API 路由之后
#    计算 frontend 文件夹的绝对路径
#    (app.py -> backend -> GoldApp -> frontend)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")