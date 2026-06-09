import sys
import os
sys.path.insert(0, 'E:/Agent/Agent_vue/backend')
os.chdir('E:/Agent/Agent_vue/backend')

try:
    from app.main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # 测试获取验证码
    response = client.get("/api/auth/captcha")
    print(f"获取验证码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        captcha_id = data['captcha_id']
        print(f"验证码ID: {captcha_id}")
        
        # 从Redis获取验证码
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, password='Password123@redis', decode_responses=True, socket_connect_timeout=2)
        stored = r.get(f'captcha:{captcha_id}')
        print(f"验证码: {stored}")
        
        # 测试忘记密码
        forgot_response = client.post("/api/auth/forgot-password", json={
            "username": "admin",
            "captcha_id": captcha_id,
            "captcha_code": stored
        })
        print(f"\n忘记密码响应: {forgot_response.status_code}")
        print(f"忘记密码内容: {forgot_response.text}")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
