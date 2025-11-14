import subprocess
import os

def main():
    """
    启动 Uvicorn 服务器的 Python 启动器。
    
    它会自动将当前工作目录更改为 'backend' 文件夹，
    然后再执行 uvicorn。
    这确保了 'backend' 内部的所有相对导入 (如 'from cache import ...') 都能正常工作。
    """
    
    # 1. 获取此脚本 (run.py) 所在的绝对路径
    #    os.path.abspath(__file__) -> /path/to/SGE_Gold_Dashboard/run.py
    #    os.path.dirname(...)      -> /path/to/SGE_Gold_Dashboard
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. 构建 'backend' 文件夹的路径
    backend_dir = os.path.join(root_dir, "backend")
    
    # 3. 检查 'backend' 文件夹是否存在
    if not os.path.isdir(backend_dir):
        print(f"错误: 未找到 'backend' 文件夹。请确保 'run.py' 与 'backend' 文件夹在同一目录下。")
        print(f"期望的路径: {backend_dir}")
        return
        
    # 4. 检查 'app.py' 是否存在
    app_py_path = os.path.join(backend_dir, "app.py")
    if not os.path.isfile(app_py_path):
        print(f"错误: 在 'backend' 文件夹中未找到 'app.py'。")
        print(f"期望的路径: {app_py_path}")
        return

    print(f"--- 黄金仪表盘启动器 ---")
    print(f"工作目录将切换至: {backend_dir}")
    print(f"正在启动 Uvicorn (uvicorn app:app --reload)...")
    print("-" * 30)

    # 5. 执行 Uvicorn 命令
    #    cwd=backend_dir 是关键:
    #    它告诉 subprocess 在执行命令前，先 'cd' 到 backend_dir
    try:
        subprocess.run(
            ["uvicorn", "app:app", "--reload"], 
            cwd=backend_dir,
            check=True
        )
    except FileNotFoundError:
        print("\n[错误] 未找到 'uvicorn' 命令。")
        print("请确保您已在 Python 环境中安装了 uvicorn: pip install uvicorn")
    except subprocess.CalledProcessError as e:
        print(f"\n[错误] Uvicorn 启动失败: {e}")
    except KeyboardInterrupt:
        print("\n--- 服务器已手动停止 ---")

if __name__ == "__main__":
    main()