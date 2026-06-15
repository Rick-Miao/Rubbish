from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import Task

# 定义蓝图，'main' 是蓝图名称，__name__ 告诉 Flask 它的包路径
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/history')
def history():
    history_data = [
        {
            "date": "十一月 17, 2025",
            "items": [
                {"name": "废电池", "category": "有害垃圾", "time": "14:30", "icon": "battery.png"},
                {"name": "奶茶杯", "category": "其他垃圾", "time": "10:15", "icon": "cup.png"},
                {"name": "纸巾", "category": "其他垃圾", "time": "09:00", "icon": "tissue.png"}
            ]
        },
        {
            "date": "十一月 16, 2025",
            "items": [
                {"name": "苹果核", "category": "厨余垃圾", "time": "18:20", "icon": "apple.png"},
                {"name": "易拉罐", "category": "可回收物", "time": "12:05", "icon": "can.png"}
            ]
        },
        {
            "date": "十一月 15, 2025",
            "items": [
                {"name": "碎陶瓷", "category": "其他垃圾", "time": "16:40", "icon": "ceramic.png"}
            ]
        }
    ]
    
    # 将数据传递给 history.html 模板
    return render_template('history.html', history_data=history_data)

@bp.route('/recycle')
def recycle_detail():
    # 这里可以直接渲染模板，后续可以从 SQLite 查询该分类下的物品列表传给前端
    return render_template('category_detail.html') # 假设你保存的文件名是 index_detail.html
    # 添加完成后重定向回首页
    return redirect(url_for('main.index'))

# ==================== 新增：我的页面路由 ====================
@bp.route('/profile')
def profile():
    """我的页面"""
    return render_template('profile.html', active_page='profile')
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
