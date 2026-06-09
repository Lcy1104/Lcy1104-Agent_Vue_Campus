import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:root@localhost:5432/agent_cam"

async def check_columns():
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.connect() as conn:
        # 检查表结构
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """))
        rows = result.fetchall()
        print("users 表结构:")
        for row in rows:
            print(f"  {row[0]}: {row[1]}")
    
    await engine.dispose()

asyncio.run(check_columns())
