import cv2
import numpy as np
import pytesseract
from discord.ext import commands
import discord
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

def load_icon_templates():
    templates = {}
    samples_dir = 'samples_notext'
    icon_files = ['3h.png', '1h.png', '30m.png', '5m.png']
    for filename in icon_files:
        name = filename.split('.')[0]
        path = os.path.join(samples_dir, filename)
        templates[name] = cv2.imread(path, 0)
    return templates

def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return blurred

def detect_icons(image, templates, threshold=0.8):
    preprocessed = preprocess_image(image)
    detected_icons = []
    for icon_name, template in templates.items():
        res = cv2.matchTemplate(preprocessed, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        for pt in zip(*loc[::-1]):
            detected_icons.append((icon_name, pt, template.shape))
    return detected_icons

def extract_number(image, x, y, w, h):
    number_roi = image[y+int(h*0.5):y+h, x+int(w*0.5):x+w]
    gray = cv2.cvtColor(number_roi, cv2.COLOR_BGR2GRAY)
    
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    
    kernel = np.ones((2,2), np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    config = r'--oem 3 --psm 10 -c tessedit_char_whitelist=0123456789'
    number = pytesseract.image_to_string(opening, config=config)
    
    return ''.join(filter(str.isdigit, number))

async def process_image(attachment):
    image_data = await attachment.read()
    image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
    
    templates = load_icon_templates()
    detected_icons = detect_icons(image, templates, threshold=0.8)
    
    results = {'3h': 0, '1h': 0, '30m': 0, '5m': 0}
    
    for icon_name, (x, y), (h, w) in detected_icons:
        number = extract_number(image, x, y, w, h)
        if number:
            results[icon_name] += int(number)
    
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