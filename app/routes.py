from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import Item, Category
from flask import Blueprint, render_template, request, redirect, url_for, flash, session


# 定义蓝图，'main' 是蓝图名称，__name__ 告诉 Flask 它的包路径
bp = Blueprint('main', __name__)

# 首页路由
@bp.route('/')
def index():
    return render_template('index.html')

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
@bp.route('/about')
def about():
    return render_template('about.html')