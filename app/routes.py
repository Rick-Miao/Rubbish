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