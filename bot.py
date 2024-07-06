import cv2
import numpy as np
import pytesseract
from discord.ext import commands
import discord
import os
from dotenv import load_dotenv
import io
import logging

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 他の関数は変更なし

async def process_image(attachment):
    try:
        image_data = await attachment.read()
        logger.debug(f"Read image data, size: {len(image_data)} bytes")
        
        nparr = np.frombuffer(image_data, np.uint8)
        logger.debug(f"Converted to numpy array, shape: {nparr.shape}")
        
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        logger.debug(f"Decoded image, shape: {image.shape if image is not None else 'None'}")
        
        if image is None:
            raise ValueError("画像の読み込みに失敗しました")
        
        if image.size == 0:
            raise ValueError("空の画像です")
        
        detected_icons = detect_icons(image)
        logger.debug(f"Detected icons: {detected_icons}")
        
        results = {'3h': 0, '1h': 0, '30m': 0, '5m': 0}
        
        for icon, (x, y, w, h) in detected_icons.items():
            number = extract_number(image, x, y, w, h)
            results[icon] = number
            logger.debug(f"Extracted number for {icon}: {number}")
        
        return results
    except Exception as e:
        logger.exception("画像処理中にエラーが発生しました")
        raise

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(('.png', '.jpg', '.jpeg')):
                try:
                    logger.info(f"Processing image: {attachment.filename}")
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

# 他のコードは変更なし

TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)