import sys
sys.path.insert(0, 'E:/Agent/Agent_vue/backend')

from app.core.security import create_access_token, verify_token

# 创建测试 token
token_data = {"sub": "test-user-id", "username": "test", "role": "admin"}
token = create_access_token(token_data)
print(f"生成的 token: {token}")

# 验证 token
payload = verify_token(token)
print(f"验证结果: {payload}")

# 测试从日志中的 token
test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiY2QwYmUwMC1iZTZjLTQ0NTEtOGVjYi0xMzExN2UzMDhhZDEiLCJ1c2VybmFtZSI6ImFkbWluIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzc5ODA2NDU5fQ.fPOG8TYQ3wgNVSdBH2eRU07oUvEf69V-bDxuljU5CLE"
payload2 = verify_token(test_token)
print(f"日志中的 token 验证结果: {payload2}")
