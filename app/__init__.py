import os
from pathlib import Path
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
load_dotenv()

db = SQLAlchemy()

# 获取项目根目录路径
BASE_DIR = Path(__file__).resolve().parent.parent

def create_app():
    app = Flask(__name__)

    # 2. 从环境变量读取配置
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'DefaultSecretKey')

    # 3. 动态解析 SQLite 数据库路径
    db_uri = os.environ.get('DATABASE_URL', 'sqlite:///instance/app.db')
    if db_uri.startswith('sqlite:///'):
        # 提取 sqlite:/// 之后的路径部分
        relative_path = db_uri.replace('sqlite:///', '')
        db_path = BASE_DIR / relative_path
        # 确保 instance 目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    else:
        # 支持其他数据库 URI 格式 (如 MySQL/PostgreSQL)
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = str(BASE_DIR / 'instance' / 'uploads')

    # 初始化扩展
    db.init_app(app)

    # 注册蓝图
    from app import routes
    app.register_blueprint(routes.bp)

    # 自动建表
    with app.app_context():
        from app import models
        db.create_all()

    return app