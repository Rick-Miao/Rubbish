from app import db
from datetime import datetime


# 1. 用户模型 (对应图中左侧 "用户" 实体)
class User(db.Model):
    __tablename__ = 'users'

    # 主键：用户ID
    user_id = db.Column(db.Integer, primary_key=True, name='user_id')
    nickname = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    # 【新增】头像字段，给一个默认头像的占位图链接
    avatar = db.Column(db.String(200), default='https://via.placeholder.com/140?text=Avatar') 
    user_type = db.Column(db.String(20), default='normal')  # 用户类别，默认为normal，可以改
    created_at = db.Column(db.DateTime, default=datetime.now)

    # 关系：一个用户可以有多条识别记录
    records = db.relationship('Record', backref='user', lazy='dynamic')
    # 关系：一个用户可以提交多条纠错反馈
    feedbacks = db.relationship('Feedback', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.nickname}>'


# 2. 垃圾类别模型 (对应图中右下角 "垃圾类别" 实体)
class Category(db.Model):
    __tablename__ = 'categories'

    # 主键：类别ID
    category_id = db.Column(db.Integer, primary_key=True, name='category_id')
    name = db.Column(db.String(50), nullable=False)  # 类别名称
    guide = db.Column(db.Text)                       # 分类指南，填写图片地址

    # 关系：一个类别包含多个垃圾物品
    items = db.relationship('Item', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


# 3. 垃圾物品模型
class Item(db.Model):
    __tablename__ = 'items'

    # 主键：物品ID
    item_id = db.Column(db.Integer, primary_key=True, name='item_id')
    name = db.Column(db.String(100), nullable=False)  # 物品名称
    description = db.Column(db.Text)                  # 物品描述
    item_url = db.Column(db.String(200))             # 物品图片不知道以什么形式存储，这里先存储图片URL
    precautions = db.Column(db.Text)                  # 注意事项
    high_freq_verify = db.Column(db.Boolean, default=False) # 高频易错验证,暂定Bool

    # 外键：关联到垃圾类别表
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)

    # 关系：一个物品会有多条识别记录指向它
    records = db.relationship('Record', backref='identified_item', lazy='dynamic')

    def __repr__(self):
        return f'<Item {self.name}>'


# 4. 识别记录模型 (对应图中中间 "识别记录" 实体)
class Record(db.Model):
    __tablename__ = 'records'

    # 主键：记录ID
    id_record = db.Column(db.Integer, primary_key=True, name='record_id')
    confidence = db.Column(db.Float)                  # 置信度
    identify_time = db.Column(db.DateTime, default=datetime.now) # 识别时间
    verify_status = db.Column(db.String(20), default='pending')  # 纠错验证状态 (如: pending, verified, rejected)

    # 外键：关联到用户表
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    # 外键：关联到垃圾物品表 (被识别为哪个物品)
    item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'), nullable=False)

    # 关系：一条记录可能产生一条纠错反馈 (1对1关系，uselist=False)
    feedback = db.relationship('Feedback', backref='source_record', uselist=False)

    def __repr__(self):
        return f'<Record {self.id} - Item {self.item_id}>'


# 5. 纠错反馈模型 (对应图中下方 "纠错反馈" 实体)
class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    # 主键：反馈ID
    feedback_id = db.Column(db.Integer, primary_key=True, name='feedback_id')
    content = db.Column(db.Text, nullable=False)      # 反馈内容
    feedback_time = db.Column(db.DateTime, default=datetime.now)

    # 外键：关联到识别记录表 (针对哪条记录)
    record_id = db.Column(db.Integer, db.ForeignKey('records.record_id'), nullable=False, unique=True)
    # 【新增】外键：关联到用户表，告诉 SQLAlchemy 这条反馈属于哪个用户
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    def __repr__(self):
        return f'<Feedback {self.id} by User {self.user_id}>'