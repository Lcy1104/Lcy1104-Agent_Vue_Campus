import time

start = time.time()

from app.utils.captcha import captcha_service

end = time.time()
print(f"导入时间: {(end-start)*1000:.0f}ms")

# 测试创建验证码
start2 = time.time()
id, img = captcha_service.create()
end2 = time.time()
print(f"创建时间: {(end2-start2)*1000:.0f}ms")
