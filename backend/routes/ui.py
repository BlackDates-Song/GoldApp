from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "..", "frontend"))

@router.get("/")
async def read_index():
    html_file_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(html_file_path):
         print(f"--- 致命错误: 在这个路径找不到 index.html ---")
         print(f"--- 正在寻找: {html_file_path} ---")
         return {"message": "错误: index.html 文件未找到！", "path": html_file_path}
         
    return FileResponse(html_file_path)