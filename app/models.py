'''
models.py - 定义数据库模型
包含用户、垃圾类别、垃圾物品、识别记录和纠错反馈等核心数据结构
缪彭哲、尤嘉晨、常凯吉、梁铭轩
创建于2026-06-15
'''
from app import db
from datetime import datetime


# 用户模型
class User(db.Model):
    __tablename__ = 'users'

    # 主键：用户ID
    user_id = db.Column(db.Integer, primary_key=True, name='user_id')
    nickname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    # 用户头像URL，默认使用占位图
    avatar = db.Column(db.String(200), default='https://via.placeholder.com/140?text=Avatar') 
    # 用户类型，默认为普通用户(normal)，可以修改为管理员(super)
    user_type = db.Column(db.String(20), default='normal')
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关联该用户的所有识别记录
    records = db.relationship('Record', backref='user', lazy='dynamic')
    # 关联该用户的所有纠错反馈
    feedbacks = db.relationship('Feedback', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.nickname}>'


# 垃圾类别模型
class Category(db.Model):
    __tablename__ = 'categories'

    # 主键：类别ID
    category_id = db.Column(db.Integer, primary_key=True, name='category_id')
    name = db.Column(db.String(50), nullable=False)  # 类别名称
    guide = db.Column(db.Text)                       # 分类指南

    # 关联该类别下的所有垃圾物品
    items = db.relationship('Item', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


# 垃圾物品模型
class Item(db.Model):
    __tablename__ = 'items'

    # 主键：物品ID
    item_id = db.Column(db.Integer, primary_key=True, name='item_id')
    name = db.Column(db.String(100), nullable=False)  # 物品名称
    description = db.Column(db.Text)                  # 物品描述
    item_url = db.Column(db.String(200))             # 物品图片URL
    precautions = db.Column(db.Text)                  # 投放注意事项
    high_freq_verify = db.Column(db.Boolean, default=False) # 是否为高频易错物品

    # 外键：关联所属的垃圾类别
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)

    # 关联指向该物品的所有识别记录
    records = db.relationship('Record', backref='identified_item', lazy='dynamic')

    def __repr__(self):
        return f'<Item {self.name}>'


# 识别记录模型
class Record(db.Model):
    __tablename__ = 'records'

    # 主键：记录ID
    id_record = db.Column(db.Integer, primary_key=True, name='record_id')
    # 识别置信度
    confidence = db.Column(db.Float)
    # 识别时间      
    identify_time = db.Column(db.DateTime, default=datetime.now)
    # 纠错验证状态（pending: 未提交, waiting: 待审核, verified: 已确认, rejected: 已驳回）
    verify_status = db.Column(db.String(20), default='pending')

    # 外键：关联执行识别的用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    # 外键：关联被识别出的垃圾物品
    item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'), nullable=False)

    # 关联针对此记录的纠错反馈
    feedback = db.relationship('Feedback', backref='source_record', uselist=False)

    def __repr__(self):
        return f'<Record {self.id} - Item {self.item_id}>'


# 纠错反馈模型
class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    # 主键：反馈ID
    feedback_id = db.Column(db.Integer, primary_key=True, name='feedback_id')
    # 反馈内容
    content = db.Column(db.Text, nullable=False)
    # 反馈时间
    feedback_time = db.Column(db.DateTime, default=datetime.now)

    # 外键：关联产生该反馈的识别记录
    record_id = db.Column(db.Integer, db.ForeignKey('records.record_id'), nullable=False, unique=True)
    # 外键：关联提交反馈的用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    def __repr__(self):
        return f'<Feedback {self.id} by User {self.user_id}>'