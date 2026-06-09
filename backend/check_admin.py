import asyncio
import sys
sys.path.insert(0, 'E:/Agent/Agent_vue/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from passlib.context import CryptContext

DATABASE_URL = "postgresql+asyncpg://postgres:root@localhost:5432/agent_cam"

# 创建密码上下文
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

async def check_admin():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, username, password_hash, role, registration_status, force_password_change FROM users WHERE username = 'admin'"))
        row = result.fetchone()
        
        if row:
            print(f"找到用户: {row.username}")
            print(f"用户ID: {row.id}")
            print(f"角色: {row.role}")
            print(f"注册状态: {row.registration_status}")
            print(f"需要修改密码: {row.force_password_change}")
            print(f"密码哈希: {row.password_hash[:50]}...")
            
            # 测试密码验证
            test_password = "admin123"
            is_valid = pwd_context.verify(test_password, row.password_hash)
            print(f"\n密码验证结果: {is_valid}")
        else:
            print("未找到 admin 用户")
    
    await engine.dispose()

asyncio.run(check_admin())
