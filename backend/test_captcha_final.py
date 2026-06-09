import sys
sys.path.insert(0, 'E:/Agent/Agent_vue/backend')

from app.utils.captcha import captcha_service
import time

# 测试创建验证码
start = time.time()
captcha_id, img = captcha_service.create()
end = time.time()

print(f"验证码ID: {captcha_id}")
print(f"图片长度: {len(img)} 字符")
print(f"生成时间: {(end-start)*1000:.0f}ms")

# 测试验证
test_code = "ABC123"  # 假设的验证码
result, msg = captcha_service.verify(captcha_id, test_code)
print(f"验证结果: {result}, 消息: {msg}")
