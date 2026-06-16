import os
from pathlib import Path
from datetime import datetime

# Flask 相关工具统一导入
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# 数据库与模型统一导入
from app import db
from app.models import Item, Category, User 

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
    return render_template('index.html')

# ================== 真实数据库版：登录与注册模块 ==================

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. 接收前端表单数据
        email = request.form.get('email')
        nickname = request.form.get('nickname')
        password = request.form.get('password')
        
        # 2. 查重校验：去数据库里找找，这个邮箱是不是已经被注册了？
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('该邮箱已被注册，请直接登录或使用其他邮箱。')
            return redirect(url_for('main.register'))

        # 3. 密码加密：生成一串别人看不懂的乱码（哈希值）
        hashed_password = generate_password_hash(password)
        
        # 4. 创建新用户对象
        new_user = User(
            email=email, 
            nickname=nickname, 
            password=hashed_password
            # avatar 字段在 models.py 里已经设了默认值，所以这里不传也可以
        )
        
        # 5. 存入数据库！
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
    return render_template('category_detail.html')

# 物品详情路由，URL 中包含物品名称参数
# TODO: 后续可以改成 item_id，避免物品名称重复导致的问题
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
    items = Item.query.filter_by(high_freq_verify=True).order_by(Item.item_id.desc()).all()

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
    
    # 2. 可选：保存文件到服务器（临时）
    filename = secure_filename(file.filename)
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
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

    if not results or len(results[0].boxes) == 0:
        predicted_category = '未检测到目标'
    else:
        result = results[0]
        boxes = result.boxes
        best_idx = int(boxes.conf.argmax().item()) if boxes.conf is not None else 0
        class_id = int(boxes.cls[best_idx].item())
        predicted_category = result.names.get(class_id, str(class_id))

    # 删除临时文件
    try:
        os.remove(filepath)
    except OSError:
        pass

    return jsonify({'category': predicted_category})


def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
@bp.route('/about')
def about():
    return render_template('about.html')
