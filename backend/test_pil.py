import time
from PIL import Image, ImageDraw, ImageFont
import random
import base64
from io import BytesIO

start = time.time()

# 简单测试
width, height = 140, 40
image = Image.new('RGB', (width, height), (240, 240, 240))
draw = ImageDraw.Draw(image)

try:
    font = ImageFont.truetype("arial.ttf", 24)
except:
    font = ImageFont.load_default()

# 绘制简单文字
code = "ABC123"
for i, char in enumerate(code):
    x = 15 + i * 20
    y = 8
    draw.text((x, y), char, font=font, fill=(50, 50, 50))

# 转换为 Base64
buffer = BytesIO()
image.save(buffer, format='PNG')
image_base64 = base64.b64encode(buffer.getvalue()).decode()

end = time.time()
print(f"生成时间: {(end-start)*1000:.0f}ms")
