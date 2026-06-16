import os
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Flask 相关工具统一导入
from flask import Blueprint, render_template, request, redirect, send_from_directory, url_for, flash, jsonify, current_app, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# 数据库与模型统一导入
from app import db
from app.models import Item, Category, User, Record
import uuid  # 用于生成唯一的文件名

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    

MODEL_FILE = Path(__file__).resolve().parent / 'best.pt'
yolo_model = None
if YOLO is not None and MODEL_FILE.exists():
    yolo_model = YOLO(MODEL_FILE)


bp = Blueprint('main', __name__)

# 首页路由
@bp.route('/')
def index():
    high_freq_items = Item.query.filter_by(high_freq_verify='True').order_by(Item.item_id.desc()).limit(4).all()

    return render_template('index.html', high_freq_items=high_freq_items)

# ================== 真实数据库版：登录与注册模块 ==================

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. 接收前端文本数据
        email = request.form.get('email')
        nickname = request.form.get('nickname')
        password = request.form.get('password')
        
        # 2. 查重校验
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('该邮箱已被注册，请直接登录或使用其他邮箱。')
            return redirect(url_for('main.register'))

        # 3. 密码加密
        hashed_password = generate_password_hash(password)
        
        # 4. 【新增：处理头像文件上传】
        # 默认给一个占位图，如果用户没传头像就用这个
        avatar_url = 'https://via.placeholder.com/140?text=Avatar' 
        
        if 'avatar' in request.files:
            file = request.files['avatar']
            # 如果用户真的选中了一个文件
            if file and file.filename != '':
                # 提取文件的后缀名 (比如 jpg, png)
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
                
                # 用 uuid 生成一个绝对不会重复的文件名，防止图片被覆盖，也防止中文名乱码报错
                filename = f"avatar_{uuid.uuid4().hex}.{ext}"
                
                # 设定保存目录为 app/static/images/avatars
                avatar_dir = os.path.join('app', 'static', 'images', 'avatars')
                os.makedirs(avatar_dir, exist_ok=True) # 如果没有这个文件夹，自动创建
                
                # 保存物理文件到你的电脑/服务器上
                filepath = os.path.join(avatar_dir, filename)
                file.save(filepath)
                
                # 生成给网页调用的静态路径
                avatar_url = url_for('static', filename=f'images/avatars/{filename}')
        
        # 5. 创建新用户对象，这次把真实头像路径传进去
        new_user = User(
            email=email, 
            nickname=nickname, 
            password=hashed_password,
            avatar=avatar_url
        )
        
        # 6. 存入数据库！
        db.session.add(new_user)
        db.session.commit()
        
        flash('注册成功！请使用刚注册的账号登录。')
        return redirect(url_for('main.login'))
        
    return render_template('register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 1. 接收前端传来的登录信息
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 2. 从数据库中寻找这个邮箱对应的用户
        user = User.query.filter_by(email=email).first()
        
        # 3. 如果用户存在，并且 (数据库里的加密密码 与 用户刚输入的密码 匹配)
        if user and check_password_hash(user.password, password):
            # 登录成功，记住这个用户的 ID
            session['user_id'] = user.user_id
            
            # (可选) 更新最后登录时间，存入数据库
            user.last_login_time = datetime.now()
            db.session.commit()
            
            return redirect(url_for('main.profile'))
        else:
            # 登录失败
            flash('邮箱或密码错误，请重试！')
            
    return render_template('login.html')


@bp.route('/logout')
def logout():
    # 退出登录：清空 session 记忆
    session.clear()
    return redirect(url_for('main.login'))


@bp.route('/profile')
def profile():
    # 安全拦截：如果没有 user_id 的记忆，说明没登录，踢回登录页
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
        
    # 从数据库中实时获取该用户的最新信息
    user = User.query.get(session['user_id'])
    
    # 防御性编程：万一数据库被清空了，但浏览器还有记忆
    if not user:
        session.clear()
        return redirect(url_for('main.login'))
        
    # 把从数据库查出来的 user 对象直接传给前端模板
    return render_template('profile.html', user=user)

# 识别历史路由
@bp.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    records = Record.query.filter_by(user_id=session['user_id']).order_by(Record.identify_time.desc()).all()
    grouped_data = defaultdict(list)
    for record in records:
        # 格式化日期 (例如: 2026-06-16)
        date_str = record.identify_time.strftime('%Y-%m-%d')
        
        # 格式化时间 (例如: 14:30)
        time_str = record.identify_time.strftime('%H:%M')
        
        # 【核心】：利用 backref 获取关联的物品和分类名称
        # record.identified_item 会返回 Item 对象
        item_obj = record.identified_item
        item_name = item_obj.name if item_obj else '未知物品'
        
        # item_obj.category 会返回 Category 对象
        category_name = item_obj.category.name if item_obj and item_obj.category else '未知分类'
        
        timestamp_ms = int(record.identify_time.timestamp() * 1000)
        
        # 将数据组装成前端需要的字典格式
        grouped_data[date_str].append({
            'name': item_name,
            'category': category_name,
            'time': time_str,
            'item_name': item_name,
            'timestamp': timestamp_ms
        })
    history_data = [{'date': k, 'items': v} for k, v in grouped_data.items()]
    
    # 将数据传递给 history.html 模板
    return render_template('history.html', history_data=history_data)

@bp.route('/category/<int:category_id>')
def category_detail(category_id):
    category = Category.query.get(category_id)
    if not category:
        flash('未找到该分类的信息')
        return redirect(url_for('main.index'))
    items = category.items.all()  # 获取该分类下的所有物品
    color_map = {
        '可回收物': '#266c86',
        '有害垃圾': '#ff1504',
        '厨余垃圾': '#26ac04',
        '其他垃圾': '#261504'
    }
    category_color = color_map.get(category.name, '#6c757d')
    return render_template('category_detail.html', category=category, items=items, category_color=category_color)

# 物品详情路由，URL 中包含物品名称参数
@bp.route('/detail/<item_name>')
def detail(item_name):
    # 从数据库查询物品详情
    item = Item.query.filter_by(name=item_name).first()
    if not item:
        # 如果数据库里没有这个物品
        flash(f'未找到 "{item_name}" 的相关信息')
        return redirect(url_for('main.index'))
    data = {
        'name': item.name,
        'description': item.description,
        'item_url': item.item_url,
        'precautions': item.precautions,
        'category': item.category.name,
    }

    return render_template('detail.html', item=data)

@bp.route('/search')
def search():
    hot_searches = ['使用过的塑料袋', '口红', '防震泡沫', '牛奶纸盒']
    return render_template('search.html', hot_searches=hot_searches)


@bp.route('/high-frequency')
def high_frequency_list():
    """
    获取高频垃圾列表页面
    """
    # 查询逻辑：查找标记为高频(hign_freq_verify)的物品，并按ID倒序排列
    # 同时预加载关联的 category 类别信息，避免在模板中产生 N+1 查询问题
    items = Item.query.filter_by(high_freq_verify='True').order_by(Item.item_id.desc()).all()

    return render_template('high_frequency.html', items=items)

@bp.route('/identify_image', methods=['POST'])
def identify_image():
    # 1. 检查是否有图片文件
    if 'image' not in request.files:
        return jsonify({'error': '没有图片文件'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式'}), 400
    
    # 2. 保存文件到服务器
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
    # 使用毫秒级时间戳，防止高并发下同一秒上传导致文件名冲突
    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}.{ext}"
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join('app', 'static', 'uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    
    # ==========================================
    # 3. 这里调用你的垃圾分类识别模型
    # ==========================================
    if yolo_model is None:
        return jsonify({'error': 'YOLO 模型未加载，请安装 ultralytics 并把 best.pt 放在 app/ 目录下'}), 500

    try:
        results = yolo_model.predict(source=filepath, save=False, device='cpu', conf=0.25)
    except Exception as e:
        return jsonify({'error': f'模型推理异常：{e}'}), 500

    predicted_name = '暂未收录'
    confidence = 0.0

    if results and len(results[0].boxes) > 0:
        result = results[0]
        boxes = result.boxes
        best_idx = int(boxes.conf.argmax().item())
        class_id = int(boxes.cls[best_idx].item())
        predicted_name = result.names.get(class_id, '暂未收录')
        confidence = float(boxes.conf[best_idx].item())

    if 'user_id' in session:
        # 去数据库查询识别出的物品（包括“暂未收录”）
        item_obj = Item.query.filter_by(name=predicted_name).first()
        
        # 如果数据库里有这个物品，就创建记录
        if item_obj:
            record_time = datetime.fromtimestamp(timestamp / 1000.0)
            new_record = Record(
                user_id=session['user_id'],
                item_id=item_obj.item_id,
                confidence=confidence,
                identify_time=record_time
                # verify_status 在 models.py 里已有默认值，无需手动传
            )
            db.session.add(new_record)
            db.session.commit()
    return jsonify({'name': predicted_name})


def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
@bp.route('/about')
def about():
    return render_template('about.html')
@bp.route('/guide')
def guide():
    return render_template('guide.html')

# 提供上传文件的访问
@bp.route('/uploads/<filename>')
def uploaded_file(filename):
    # 获取 instance 目录下的 uploads 文件夹
    uploads_dir = os.path.join(current_app.instance_path, 'uploads')
    return send_from_directory(uploads_dir, filename)