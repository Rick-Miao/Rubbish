import os
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from app import db
from app.models import Item, Category
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from werkzeug.utils import secure_filename

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

MODEL_FILE = Path(__file__).resolve().parent / 'best.pt'
yolo_model = None
if YOLO is not None and MODEL_FILE.exists():
    yolo_model = YOLO(MODEL_FILE)

# 定义蓝图，'main' 是蓝图名称，__name__ 告诉 Flask 它的包路径
bp = Blueprint('main', __name__)

# 首页路由
@bp.route('/')
def index():
    high_freq_items = Item.query.filter_by(high_freq_verify='True').order_by(Item.item_id.desc()).limit(4).all()

    return render_template('index.html', high_freq_items=high_freq_items)

# ================== 登录与注册模块 ==================

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # 接收前端表单数据
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 【模拟数据库校验】写死一个测试账号
        if email == 'admin@test.com' and password == '123456':
            # 登录成功，将用户信息存入 session
            session['user_id'] = 1
            session['nickname'] = '学术委员'
            session['email'] = 'admin@test.com'
            session['avatar'] = 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?ixlib=rb-4.0.3&auto=format&fit=crop&w=150&q=80'
            return redirect(url_for('main.profile'))
        else:
            # 登录失败，发送报错提示
            flash('账号或密码错误（请用测试账号: admin@test.com / 123456）')
            
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 接收注册表单 (这里模拟直接成功)
        flash('注册成功！请使用刚注册的账号登录。')
        return redirect(url_for('main.login'))
        
    return render_template('register.html')

@bp.route('/logout')
def logout():
    # 清除 session 中的登录状态
    session.clear()
    return redirect(url_for('main.login'))

@bp.route('/profile')
def profile():
    # 核心拦截逻辑：如果 session 里没有 user_id，说明没登录，强制踢回登录页
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
        
    # 如果已登录，把 session 里的数据打包成字典传给模板
    mock_user = {
        'nickname': session.get('nickname'),
        'email': session.get('email'),
        'avatar': session.get('avatar')
    }
    return render_template('profile.html', user=mock_user)

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
