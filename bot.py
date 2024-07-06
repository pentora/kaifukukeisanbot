import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging
import io
from PIL import Image
import numpy as np
from pytesseract import pytesseract

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

def is_similar_color(color1, color2, threshold=30):
    return sum(abs(c1 - c2) for c1, c2 in zip(color1, color2)) < threshold

def find_icon_regions(image):
    width, height = image.size
    icon_colors = {
        '3h': (255, 193, 7),  # 黄色
        '1h': (233, 30, 99),  # マゼンタ
        '30m': (33, 150, 243),  # 青
        '5m': (76, 175, 80)  # 緑
    }
    
    regions = {icon: [] for icon in icon_colors}
    
    for y in range(0, height, 10):  # 10ピクセルごとにスキャン
        for x in range(0, width, 10):
            color = image.getpixel((x, y))
            for icon, target_color in icon_colors.items():
                if is_similar_color(color, target_color):
                    regions[icon].append((x, y))
    
    return regions

def extract_number(image, region):
    x, y = region
    roi = image.crop((x, y, x + 100, y + 50))  # 領域を適宜調整
    gray = roi.convert('L')
    threshold = 200
    binary = gray.point(lambda x: 0 if x < threshold else 255, '1')
    
    config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789,'
    number = pytesseract.image_to_string(binary, config=config)
    number = ''.join(filter(str.isdigit, number))
    return int(number) if number else 0

async def process_image(attachment):
    try:
        image_data = await attachment.read()
        logger.debug(f"Read image data, size: {len(image_data)} bytes")
        
        with Image.open(io.BytesIO(image_data)) as img:
            logger.debug(f"PIL Image size: {img.size}, mode: {img.mode}")
            
            icon_regions = find_icon_regions(img)
            logger.debug(f"Detected icon regions: {icon_regions}")
            
            results = {'3h': 0, '1h': 0, '30m': 0, '5m': 0}
            
            for icon, regions in icon_regions.items():
                if regions:
                    number = extract_number(img, regions[0])  # 最初に見つかった領域を使用
                    results[icon] = number
                    logger.debug(f"Extracted number for {icon}: {number}")
        
        return results
    except Exception as e:
        logger.exception("画像処理中にエラーが発生しました")
        raise

def calculate_total_time(results):
    total_hours = results['3h'] * 3 + results['1h'] + results['30m'] * 0.5 + results['5m'] / 12
    return total_hours

@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(('.png', '.jpg', '.jpeg')):
                try:
                    logger.info(f"Processing image: {attachment.filename}, size: {attachment.size} bytes, url: {attachment.url}")
                    results = await process_image(attachment)
                    total_time = calculate_total_time(results)
                    
                    response = "検出されたアイコンと数量:\n"
                    for icon in ['3h', '1h', '30m', '5m']:
                        response += f"{icon}: {results[icon]}個\n"
                    
                    response += f"\n計算結果: {results['3h']} * 3 + {results['1h']} + {results['30m']} * 0.5 + {results['5m']} / 12 = {total_time:.2f}\n"
                    response += f"合計 {total_time:.2f} 時間"
                    
                    await message.reply(response)
                except Exception as e:
                    error_message = f'画像の処理中にエラーが発生しました: {str(e)}'
                    logger.error(error_message)
                    await message.reply(error_message)
                break

    await bot.process_commands(message)

TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)