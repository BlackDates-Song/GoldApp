# --- 1. 基础镜像 ---
# 使用一个轻量级的、与您开发环境一致的 Python 版本
FROM python:3.11-slim

# --- 2. 设置工作目录 ---
# 在容器内创建一个 /app 目录
WORKDIR /app

# --- 3. 安装依赖 ---
# 仅复制 requirements.txt 文件
COPY requirements.txt .

# 运行 pip install。
# 这是 Docker 缓存优化的关键：只要 requirements.txt 不变，这一层就不会重新运行
RUN pip install --no-cache-dir -r requirements.txt

# --- 4. 复制项目代码 ---
# 将我们重构后的 backend 和 frontend 文件夹复制到 /app
COPY backend/ ./backend/
COPY frontend/ ./frontend/
# 注意：我们不再需要 run.py，因为它用于开发环境的 --reload

# --- 5. 设置最终工作目录 ---
# Uvicorn 需要在能找到 app.py 的地方运行
WORKDIR /app/backend

# --- 6. 暴露端口 ---
# 告诉 Docker 容器将监听 8080 端口
EXPOSE 8080

# --- 7. 生产环境启动命令 ---
# 这是在生产环境中运行 Uvicorn 的正确方式
# 它会运行 backend/app.py 文件中的 app 实例
# --host 0.0.0.0 允许外部访问
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]