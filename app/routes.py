'''
routes.py - 定义路由处理函数
包含登录、注册、识别等主要业务逻辑
缪彭哲、尤嘉晨、常凯吉、梁铭轩
创建于2026-06-15
'''
import os
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Flask 核心工具
from flask import Blueprint, render_template, request, redirect, send_from_directory, url_for, flash, jsonify, current_app, session
from werkzeug.security import generate_password_hash, check_password_hash

# 数据库与模型导入
from app import db
from app.models import Item, Category, User, Record, Feedback
import uuid

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    
# 初始化 YOLO 模型
MODEL_FILE = Path(__file__).resolve().parent / 'best.pt'
yolo_model = None
if YOLO is not None and MODEL_FILE.exists():
    yolo_model = YOLO(MODEL_FILE)

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """首页路由：展示高频易错物品"""
    high_freq_items = Item.query.filter_by(high_freq_verify='True').order_by(Item.item_id.desc()).limit(4).all()
    return render_template('index.html', high_freq_items=high_freq_items)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """注册路由：处理用户注册逻辑，包括文本数据和头像上传"""
    if request.method == 'POST':
        email = request.form.get('email')
        nickname = request.form.get('nickname')
        password = request.form.get('password')
        
        # 校验邮箱唯一性
        if User.query.filter_by(email=email).first():
            flash('该邮箱已被注册，请直接登录或使用其他邮箱。')
            return redirect(url_for('main.register'))

        # 密码哈希加密
        hashed_password = generate_password_hash(password)
        
        # 处理头像上传
        # 默认占位图
        avatar_url = 'https://via.placeholder.com/140?text=Avatar' 
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '':
                # 提取后缀并使用 UUID 生成唯一文件名，避免重名覆盖及中文编码问题
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
                filename = f"avatar_{uuid.uuid4().hex}.{ext}"
                
                # 保存文件至静态目录
                avatar_dir = os.path.join('app', 'static', 'images', 'avatars')
                os.makedirs(avatar_dir, exist_ok=True)
                file.save(os.path.join(avatar_dir, filename))
                
                # 生成静态资源访问路径
                avatar_url = url_for('static', filename=f'images/avatars/{filename}')
        
        # 创建用户并持久化
        new_user = User(
            email=email, 
            nickname=nickname, 
            password=hashed_password,
            avatar=avatar_url
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('注册成功！请使用刚注册的账号登录。')
        return redirect(url_for('main.login'))
        
    return render_template('register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录路由：处理用户登录逻辑，验证邮箱和密码，并使用 session 记住登录状态"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        # 验证账号与密码
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.user_id

            db.session.commit()
            
            return redirect(url_for('main.profile'))
        else:
            flash('邮箱或密码错误，请重试！')
            
    return render_template('login.html')


@bp.route('/logout')
def logout():
    """登出路由：清除 session 中的登录状态，并重定向回登录页"""
    session.clear()
    return redirect(url_for('main.login'))


@bp.route('/profile')
def profile():
    """个人资料路由：显示当前登录用户的个人信息"""
    # 登录状态拦截
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
        
    user = User.query.get(session['user_id'])
    
    # 防止 Session 中的用户 ID 在数据库中已失效
    if not user:
        session.clear()
        return redirect(url_for('main.login'))
        
    return render_template('profile.html', user=user)


@bp.route('/history')
def history():
    """历史记录路由：展示当前用户的识别历史，按日期分组显示，并利用 backref 获取关联的物品和分类信息"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    records = Record.query.filter_by(user_id=session['user_id']).order_by(Record.identify_time.desc()).all()
    
    # 按日期分组聚合数据
    grouped_data = defaultdict(list)
    for record in records:
        date_str = record.identify_time.strftime('%Y-%m-%d')
        time_str = record.identify_time.strftime('%H:%M')
        
        # 通过外键关联获取物品与分类名称
        item_obj = record.identified_item
        item_name = item_obj.name if item_obj else '未知物品'
        category_name = item_obj.category.name if item_obj and item_obj.category else '未知分类'
        
        timestamp_ms = int(record.identify_time.timestamp() * 1000)

        grouped_data[date_str].append({
            'name': item_name,
            'category': category_name,
            'time': time_str,
            'item_name': item_name,
            'timestamp': timestamp_ms,
            'record_id': record.id_record
        })
    history_data = [{'date': k, 'items': v} for k, v in grouped_data.items()]
    return render_template('history.html', history_data=history_data)


@bp.route('/category/<int:category_id>')
def category_detail(category_id):
    """分类详情路由：展示某个分类下的所有物品，并根据分类类型设置不同的主题颜色"""
    category = Category.query.get(category_id)
    if not category:
        flash('未找到该分类的信息')
        return redirect(url_for('main.index'))
    
    items = category.items.all()

    # 映射分类对应的主题色
    color_map = {
        '可回收物': '#266c86',
        '有害垃圾': '#ff1504',
        '厨余垃圾': '#26ac04',
        '其他垃圾': '#261504'
    }
    category_color = color_map.get(category.name, '#6c757d')

    return render_template('category_detail.html', category=category, items=items, category_color=category_color)


@bp.route('/detail/<item_name>')
def detail(item_name):
    """物品详情路由：展示某个物品的详细信息，并根据查询来源和审核状态决定是否显示反馈入口"""
    from_source = request.args.get('from', '')
    record_id = request.args.get('record_id', '')

    item = Item.query.filter_by(name=item_name).first()
    if not item:
        # 兜底处理：若未收录，则重定向至“暂未收录”详情页
        if item_name != '暂未收录':
            return redirect(url_for('main.detail', item_name='暂未收录', **{'from': from_source, 'record_id': record_id}))
        flash(f'未找到 "{item_name}" 的相关信息')
        return redirect(url_for('main.index'))
    
    # 获取关联记录的审核状态
    verify_status = 'pending'
    if record_id and record_id.isdigit():
        record = Record.query.get(int(record_id))
        if record:
            verify_status = record.verify_status

    data = {
        'name': item.name,
        'description': item.description,
        'item_url': item.item_url,
        'precautions': item.precautions,
        'category': item.category.name,
        'record_id': record_id,
        'verify_status': verify_status,
        'show_feedback': from_source in ['identify', 'record'] and record_id != '' and verify_status == 'pending'
    }

    return render_template('detail.html', item=data)


@bp.route('/search')
def search():
    """搜索路由：展示搜索页面，并提供一些预设的热门搜索建议"""
    hot_searches = ['塑料袋', '骨头', '塑料瓶']
    return render_template('search.html', hot_searches=hot_searches)


@bp.route('/high-frequency')
def high_frequency_list():
    """高频易错物品路由：展示标记为高频易错的物品列表，并预加载关联的类别信息以优化查询性能"""
    items = Item.query.filter_by(high_freq_verify='True').order_by(Item.item_id.desc()).all()
    return render_template('high_frequency.html', items=items)


@bp.route('/about')
def about():
    """关于我们路由：展示项目的背景、团队成员等信息"""
    return render_template('about.html')


@bp.route('/guide')
def guide():
    """分类指南路由：展示垃圾分类的相关知识和指南信息"""
    return render_template('guide.html')


@bp.route('/identify_image', methods=['POST'])
def identify_image():
    """图片识别路由：处理前端上传的图片文件，调用 YOLO 模型进行识别，并根据识别结果创建记录或返回错误信息 """
    # 校验上传文件
    if 'image' not in request.files:
        return jsonify({'error': '没有图片文件'}), 400
    
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': '未选择文件或格式不支持'}), 400
    
    # 保存文件至服务器 (使用毫秒时间戳防并发冲突)
    timestamp = int(time.time() * 1000)
    filename = f"{timestamp}.jpg"
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.instance_path, 'uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    
    # 执行 YOLO 模型推理
    if yolo_model is None:
        return jsonify({'error': 'YOLO 模型未加载'}), 500

    try:
        results = yolo_model.predict(source=filepath, save=False, device='cpu', conf=0.25)
    except Exception as e:
        return jsonify({'error': f'模型推理异常：{e}'}), 500

    # 解析预测结果
    predicted_name = '暂未收录'
    confidence = 0.0
    record_id = None

    if results and len(results[0].boxes) > 0:
        result = results[0]
        boxes = result.boxes
        best_idx = int(boxes.conf.argmax().item())
        class_id = int(boxes.cls[best_idx].item())
        predicted_name = result.names.get(class_id, '暂未收录')
        confidence = float(boxes.conf[best_idx].item())

    # 若用户已登录，则记录识别历史
    if 'user_id' in session:
        item_obj = Item.query.filter_by(name=predicted_name).first()
        if item_obj:
            record_time = datetime.fromtimestamp(timestamp / 1000.0)
            new_record = Record(
                user_id=session['user_id'],
                item_id=item_obj.item_id,
                confidence=confidence,
                identify_time=record_time
            )
            db.session.add(new_record)
            db.session.commit()
            record_id = new_record.id_record
    
    # 若未生成记录，则清理临时图片文件
    if not record_id:
        try:
            os.remove(filepath)
        except OSError:
            pass

    return jsonify({'name': predicted_name, 'record_id': record_id})


@bp.route('/uploads/<filename>')
def uploaded_file(filename):
    """图片访问路由：提供访问上传图片的接口，实际文件存储在 instance 目录下的 uploads 文件夹中，URL 路径为 /uploads/<filename>"""
    uploads_dir = os.path.join(current_app.instance_path, 'uploads')
    return send_from_directory(uploads_dir, filename)


@bp.route('/api/search_suggestions')
def search_suggestions():
    """搜索建议 API：根据前端传来的关键字参数，返回物品名称列表，支持模糊查询，并限制返回结果数量以优化性能"""
    keyword = request.args.get('keyword', '').strip()
    if not keyword:
        return jsonify([])
    
    # 模糊匹配查询，限制返回数量
    items = Item.query.filter(Item.name.like(f'%{keyword}%')).limit(5).all()
    return jsonify([item.name for item in items])


@bp.route('/admin/review')
def admin_review():
    """管理员审核路由：展示所有用户提交的纠错反馈，按日期分组显示，并利用 backref 获取关联的识别记录、物品、分类和提交反馈的用户信息 """
    # 权限校验
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    user = User.query.get(session['user_id'])
    if not user or user.user_type != 'super':
        flash('您没有权限访问该页面')
        return redirect(url_for('main.profile'))
        
    feedbacks = Feedback.query.order_by(Feedback.feedback_time.desc()).all()
    
    # 按日期分组聚合反馈数据
    grouped_data = defaultdict(list)
    for fb in feedbacks:
        date_str = fb.feedback_time.strftime('%Y-%m-%d')
        time_str = fb.feedback_time.strftime('%H:%M')
        
        # 关联查询物品、分类及用户信息
        record = fb.source_record
        item_obj = record.identified_item if record else None  # 获取对应的 Item 对象
        
        item_name = item_obj.name if item_obj else '未知物品'
        category_name = item_obj.category.name if item_obj and item_obj.category else '未知分类'
        timestamp_ms = int(record.identify_time.timestamp() * 1000) if record and record.identify_time else 0
        user_nickname = fb.user.nickname if fb.user else '未知用户'
        verify_status = record.verify_status if record else 'unknown'
        
        grouped_data[date_str].append({
            'feedback_id': fb.feedback_id,
            'record_id': fb.record_id,
            'item_name': item_name,
            'category': category_name,
            'content': fb.content,
            'time': time_str,
            'timestamp': timestamp_ms,
            'user_nickname': user_nickname,
            'verify_status': verify_status
        })
        
    review_data = [{'date': k, 'items': v} for k, v in grouped_data.items()]
    return render_template('admin_review.html', review_data=review_data)


@bp.route('/feedback/<int:record_id>', methods=['GET', 'POST'])
def feedback(record_id):
    """纠错反馈路由：处理用户针对某条识别记录提交的反馈，包含权限校验、重复提交校验、数据持久化等逻辑，并根据审核状态决定是否显示反馈入口"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    user_id = session['user_id']
    record = Record.query.get(record_id)

    if not record:
        flash('识别记录不存在')
        return redirect(url_for('main.index'))
        
    # 校验是否已提交过反馈
    if Feedback.query.filter_by(record_id=record_id).first():
        flash('该记录已经提交过纠错反馈，请勿重复提交！')
        item_name = record.identified_item.name if record.identified_item else '暂未收录'
        return redirect(url_for('main.detail', item_name=item_name, **{'from': 'record', 'record_id': record_id}))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash('反馈内容不能为空！')
        else:
            new_feedback = Feedback(
                content=content,
                record_id=record_id,
                user_id=user_id
            )
            db.session.add(new_feedback)

            record.verify_status = 'waiting'
            db.session.commit()
            
            flash('感谢您的反馈，管理员将尽快审核！')
            item_name = record.identified_item.name if record.identified_item else '暂未收录'
            return redirect(url_for('main.detail', item_name=item_name, **{'from': 'record', 'record_id': record_id}))
            
    return render_template('feedback.html', record_id=record_id, user_id=user_id)


@bp.route('/api/review_feedback', methods=['POST'])
def api_review_feedback():
    """管理员审核反馈 API：处理管理员对用户提交的纠错反馈进行审核的请求，包含权限校验、参数校验、数据更新等逻辑，并返回操作结果的 JSON 响应"""
    # 管理员权限校验
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    user = User.query.get(session['user_id'])
    if not user or user.user_type != 'super':
        return jsonify({'error': '权限不足'}), 403

    data = request.get_json()
    feedback_id = data.get('feedback_id')
    action = data.get('action')

    if not feedback_id or action not in ['verified', 'rejected']:
        return jsonify({'error': '参数错误'}), 400

    feedback = Feedback.query.get(feedback_id)
    if not feedback:
        return jsonify({'error': '反馈记录不存在'}), 404

    record = feedback.source_record
    if not record:
        return jsonify({'error': '关联的识别记录不存在'}), 404

    # 更新审核状态
    record.verify_status = action
    db.session.commit()

    return jsonify({'success': True, 'message': '审核状态已更新'})


def allowed_file(filename):
    """校验上传文件的扩展名，确保只接受特定格式的图片文件"""
    allowed_extensions = {'png', 'jpg', 'jpeg', 'bmp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions