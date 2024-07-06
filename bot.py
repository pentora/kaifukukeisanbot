import cv2
import numpy as np
import pytesseract
from discord.ext import commands
import discord
import os
from dotenv import load_dotenv
import io

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

def detect_icons(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    color_ranges = {
        '3h': ([20, 100, 100], [40, 255, 255]),
        '1h': ([140, 100, 100], [160, 255, 255]),
        '30m': ([100, 100, 100], [140, 255, 255]),
        '5m': ([50, 100, 100], [70, 255, 255])
    }
    
    detected_icons = {}
    
    for icon, (lower, upper) in color_ranges.items():
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            c = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(c)
            detected_icons[icon] = (x, y, w, h)
    
    return detected_icons

def preprocess_for_ocr(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    kernel = np.ones((2,2), np.uint8)
    opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    return opening

def extract_number(image, x, y, w, h):
    roi = image[y:y+h, x+w:x+w+100]
    preprocessed = preprocess_for_ocr(roi)
    
    config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789,'
    number = pytesseract.image_to_string(preprocessed, config=config)
    number = ''.join(filter(str.isdigit, number))
    return int(number) if number else 0

async def process_image(attachment):
    image_data = await attachment.read()
    nparr = np.frombuffer(image_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise ValueError("画像の読み込みに失敗しました")
    
    detected_icons = detect_icons(image)
    
    results = {'3h': 0, '1h': 0, '30m': 0, '5m': 0}
    
    for icon, (x, y, w, h) in detected_icons.items():
        number = extract_number(image, x, y, w, h)
        results[icon] = number
    
    return results

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
                    results = await process_image(attachment)
                    total_time = calculate_total_time(results)
                    
                    response = "検出されたアイコンと数量:\n"
                    for icon in ['3h', '1h', '30m', '5m']:
                        response += f"{icon}: {results[icon]}個\n"
                    
                    response += f"\n計算結果: {results['3h']} * 3 + {results['1h']} + {results['30m']} * 0.5 + {results['5m']} / 12 = {total_time:.2f}\n"
                    response += f"合計 {total_time:.2f} 時間"
                    
                    await message.reply(response)
                except Exception as e:
                    await message.reply(f'画像の処理中にエラーが発生しました: {str(e)}')
                break

    await bot.process_commands(message)

TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)