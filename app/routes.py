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
# 将这段加在 routes.py 的最下方
@bp.route('/detail/<item_name>')
def detail(item_name):
    mock_data = {
        'name': item_name,
        'category': '可回收物',
        'guide': '1. 清理残留：倒掉剩余牛奶，用清水简单冲洗，避免残留液体滋生细菌或污染其他可回收物。\n2. 压扁处理：压扁牛奶盒可以减少体积，节省回收运输空间。\n3. 保持干燥：确保纸盒干燥后再投放，防止霉变影响回收质量。\n4. 分类投放：放入可回收物垃圾桶，不要与其他垃圾混合。',
        # 这里先用网络占位图，如果你们 static/images 里有图，可以换成 url_for('static', filename='...')
        'main_img': 'https://via.placeholder.com/800x400/e9ecef/6c757d?text=Milk+Carton+Cover',
        'sub_imgs': [
            'https://via.placeholder.com/200x300/e9ecef/6c757d?text=pic1',
            'https://via.placeholder.com/200x300/e9ecef/6c757d?text=pic2',
            'https://via.placeholder.com/200x300/e9ecef/6c757d?text=pic3'
        ]
    }
    
    # 把 mock_data 传给 detail.html，在模板里它就叫 'item'
    return render_template('detail.html', item=mock_data)