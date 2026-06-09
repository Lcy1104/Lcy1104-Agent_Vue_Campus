import sys
sys.path.insert(0, 'E:/Agent/Agent_vue/backend')

from app.main import app

print("FastAPI 路由列表:")
for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        methods = ','.join(route.methods)
        print(f"  {methods} {route.path}")
