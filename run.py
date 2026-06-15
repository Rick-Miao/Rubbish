from app import create_app

app = create_app()

if __name__ == '__main__':
    # host='0.0.0.0' 允许局域网内的其他设备(如手机)访问
    # debug=True 开启热重载，方便开发
    app.run(host='0.0.0.0', port=5000, debug=True)