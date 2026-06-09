"""
Captcha Utility - Using Redis
Based on need.md: backend/app/utils/captcha.py
"""
import random
import string
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import hashlib
import time
from typing import Optional
import redis
import platform

# Redis 连接（延迟初始化）
_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                password='Password123@redis',
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            _redis_client.ping()
            print("Redis connected successfully")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            _redis_client = False
    return _redis_client if _redis_client is not False else None


class CaptchaService:
    """验证码服务 - Redis存储（失败时使用内存）"""
    
    def __init__(self):
        self._expire_seconds = 300  # 5分钟过期
        self._memory_storage = {}  # 内存备用存储
    
    def _generate_code(self, length: int = 6) -> str:
        """生成随机验证码 - 6位，只包含大写字母和数字"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=length))
    
    def _generate_image(self, code: str) -> str:
        """生成验证码图片（Base64）- 简化版本"""
        width, height = 140, 40
        image = Image.new('RGB', (width, height), (240, 240, 240))
        draw = ImageDraw.Draw(image)
        
        # 使用跨平台的字体
        font = self._get_font(24)
        
        # 简化的背景噪点
        for _ in range(30):
            x = random.randint(0, width)
            y = random.randint(0, height)
            color = (random.randint(200, 230), random.randint(200, 230), random.randint(200, 230))
            draw.point((x, y), fill=color)
        
        # 少量干扰线
        for _ in range(2):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            color = (random.randint(150, 180), random.randint(150, 180), random.randint(150, 180))
            draw.line([(x1, y1), (x2, y2)], fill=color, width=1)
        
        # 计算字符位置
        char_count = len(code)
        char_width = width // (char_count + 1)
        
        # 绘制文字
        for i, char in enumerate(code):
            x = 15 + i * char_width
            y = 8
            color = (random.randint(30, 70), random.randint(30, 70), random.randint(30, 70))
            draw.text((x, y), char, font=font, fill=color)
        
        # 转换为 Base64
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{image_base64}"
    
    def _get_font(self, size):
        """获取跨平台的字体"""
        import platform
        
        system = platform.system()
        font_paths = []
        
        if system == 'Windows':
            font_paths = [
                'C:/Windows/Fonts/arial.ttf',
                'C:/Windows/Fonts/simhei.ttf',  # 黑体
            ]
        elif system == 'Linux':
            font_paths = [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
            ]
        elif system == 'Darwin':  # macOS
            font_paths = [
                '/System/Library/Fonts/Helvetica.ttc',
                '/Library/Fonts/Arial.ttf',
            ]
        
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
        
        # 如果都失败了，使用默认字体
        return ImageFont.load_default()
    
    def create(self) -> tuple[str, str]:
        """
        创建验证码
        返回: (captcha_id, base64_image)
        """
        code = self._generate_code()
        captcha_id = hashlib.sha256(f"{code}{time.time()}".encode()).hexdigest()[:16]
        image_data = self._generate_image(code)
        
        redis_client = get_redis_client()
        # 存储到 Redis（如果可用）或内存
        if redis_client:
            try:
                redis_client.setex(
                    f"captcha:{captcha_id}",
                    self._expire_seconds,
                    code.upper()
                )
            except:
                # Redis 失败，使用内存
                self._memory_storage[captcha_id] = {
                    "code": code.upper(),
                    "expires": time.time() + self._expire_seconds
                }
        else:
            # 使用内存存储
            self._memory_storage[captcha_id] = {
                "code": code.upper(),
                "expires": time.time() + self._expire_seconds
            }
        
        return captcha_id, image_data
    
    def verify(self, captcha_id: str, captcha_code: str) -> tuple[bool, str]:
        """验证验证码，返回 (是否成功, 错误信息)"""
        key = f"captcha:{captcha_id}"
        stored_code = None
        expired = False
        
        redis_client = get_redis_client()
        # 先尝试 Redis
        if redis_client:
            try:
                stored_code = redis_client.get(key)
            except:
                pass
        
        # 如果 Redis 没有，尝试内存
        if not stored_code and captcha_id in self._memory_storage:
            data = self._memory_storage[captcha_id]
            if time.time() < data["expires"]:
                stored_code = data["code"]
            else:
                # 过期删除
                expired = True
                del self._memory_storage[captcha_id]
        
        if not stored_code:
            if expired:
                return False, "验证码已过期，请重新获取"
            print(f"[DEBUG] 验证码未找到: captcha_id={captcha_id}")
            return False, "验证码错误"
        
        # 验证成功后删除
        print(f"[DEBUG] 验证码对比: 存储='{stored_code}', 输入='{captcha_code}', 输入转大写='{captcha_code.upper()}'")
        if stored_code == captcha_code.upper():
            redis_client = get_redis_client()
            try:
                if redis_client:
                    redis_client.delete(key)
            except:
                pass
            if captcha_id in self._memory_storage:
                del self._memory_storage[captcha_id]
            return True, ""
        
        return False, "验证码错误"


# 全局验证码服务实例
captcha_service = CaptchaService()
