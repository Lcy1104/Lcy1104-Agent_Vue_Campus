"""
修复 admin 密码 - 最小修改方案
运行一次即可: python fix_admin_password.py
"""
import asyncio
import sys
sys.path.insert(0, 'E:\\Agent\\Agent_vue\\backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# 数据库配置
DATABASE_URL = "postgresql+asyncpg://postgres:root@localhost:5432/agent_cam"

# Argon2 密码上下文
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

async def fix_password():
    from sqlalchemy import text
    
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # 生成正确的密码哈希 (admin123)
        correct_hash = pwd_context.hash("admin123")
        
        # 更新数据库
        await conn.execute(
            text("UPDATE users SET password_hash = :hash WHERE username = 'admin'"),
            {"hash": correct_hash}
        )
        await conn.commit()
        
        print("OK Admin 密码已修复为: admin123")
        print(f"Hash: {correct_hash[:50]}...")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_password())
