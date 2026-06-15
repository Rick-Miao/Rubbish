from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import Task

# 定义蓝图，'main' 是蓝图名称，__name__ 告诉 Flask 它的包路径
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    # 从 SQLite 数据库查询所有任务，按时间倒序排列
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return render_template('index.html', tasks=tasks)

@bp.route('/add', methods=['POST'])
def add_task():
    # 获取表单提交的数据
    title = request.form.get('title')
    if title:
        new_task = Task(title=title)
        db.session.add(new_task)
        db.session.commit()  # 提交到 SQLite
        flash('任务添加成功！', 'success')
    
    # 添加完成后重定向回首页
    return redirect(url_for('main.index'))

# ==================== 新增：我的页面路由 ====================
@bp.route('/profile')
def profile():
    """我的页面"""
    return render_template('profile.html', active_page='profile')