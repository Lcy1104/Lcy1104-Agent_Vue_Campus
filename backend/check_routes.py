import sys
sys.path.insert(0, 'E:/Agent/Agent_vue/backend')

from fastapi import FastAPI
from app.api import auth

# 创建应用
app = FastAPI()
app.include_router(auth.router)

# 列出所有路由
print("已注册的路由:")
for route in app.routes:
    if hasattr(route, 'methods'):
        print(f"  {route.methods} {route.path}")
