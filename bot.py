import cv2
import numpy as np
import pytesseract
from discord.ext import commands
import discord
import os
import io
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# アイコンテンプレートを読み込む関数
def load_icon_templates():
    templates = {}
    samples_dir = 'samples'
    icon_files = ['1h_icon.png', '3h_icon.png', '5m_icon.png', '30m_icon.png']
    for filename in icon_files:
        name = filename.split('_')[0]  # '_icon.png' を除去
        path = os.path.join(samples_dir, filename)
        templates[name] = cv2.imread(path, 0)
    return templates

# テンプレートマッチングでアイコンを検出する関数
def detect_icons(image, templates, threshold=0.8):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detected_icons = []
    for icon_name, template in templates.items():
        res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        for pt in zip(*loc[::-1]):
            detected_icons.append((icon_name, pt, template.shape))
    return detected_icons

# 数量を抽出する関数
def extract_number(image, x, y, w, h):
    number_roi = image[y+int(h*0.7):y+h, x+int(w*0.7):x+w]
    number_gray = cv2.cvtColor(number_roi, cv2.COLOR_BGR2GRAY)
    _, number_thresh = cv2.threshold(number_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    number = pytesseract.image_to_string(number_thresh, config='--psm 7 --oem 3 -c tessedit_char_whitelist=x0123456789')
    return ''.join(filter(str.isdigit, number))

# 画像を処理する関数
async def process_image(attachment):
    image_data = await attachment.read()
    image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
    
    templates = load_icon_templates()
    detected_icons = detect_icons(image, templates)
    
    results = {}
    for icon_name, (x, y), (h, w) in detected_icons:
        number = extract_number(image, x, y, w, h)
        if number:
            results[icon_name] = results.get(icon_name, 0) + int(number)
    
    return results

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
                await message.reply('画像を処理中...')
                try:
                    results = await process_image(attachment)
                    response = "検出されたアイコンと合計数量:\n"
                    for icon_name, count in results.items():
                        response += f"{icon_name}: {count}個\n"
                    await message.reply(response)
                except Exception as e:
                    await message.reply(f'画像の処理中にエラーが発生しました: {str(e)}')
                break

    await bot.process_commands(message)

TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)