import sys
sys.path.insert(0, 'E:/Agent/Agent_vue/backend')
from app.core.security import verify_password, get_password_hash

test_password = 'admin123456'
test_hash = get_password_hash(test_password)
print(f'生成的哈希: {test_hash}')
print(f'验证正确密码: {verify_password(test_password, test_hash)}')
print(f'验证错误密码: {verify_password("wrong", test_hash)}')
