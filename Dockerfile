# 1. 使用官方 Python 3.11 镜像
FROM python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制 requirements.txt (这步是为了利用 Docker 缓存)
#    我们只复制这一个文件，先安装依赖
COPY backend/requirements.txt ./backend/requirements.txt

# 4. 安装依赖
#    (注意: 你的 requirements.txt 必须包含 pytz, uvicorn, fastapi, akshare, pandas, numpy)
RUN pip install --no-cache-dir -r backend/requirements.txt

# 5. 复制你项目的 *所有* 文件 (后端和前端)
COPY . .

# 6. 暴露腾讯云 *要求* 的端口
#    (Render 使用 $PORT, 腾讯云固定使用 8080)
EXPOSE 8080

# 7. 启动命令
#    - 告诉 uvicorn 去 'backend' 目录找 'main:app'
#    - 监听所有 IP (0.0.0.0)
#    - 监听 8080 端口
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "backend"]