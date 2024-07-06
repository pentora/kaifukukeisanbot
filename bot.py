import cv2
import numpy as np
import pytesseract
from discord.ext import commands
import discord
import os
import io
from dotenv import load_dotenv
import tempfile

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

def load_icon_templates():
    templates = {}
    samples_dir = 'samples'
    icon_files = ['1h_icon.png', '3h_icon.png', '5m_icon.png', '30m_icon.png']
    for filename in icon_files:
        name = filename.split('_')[0]
        path = os.path.join(samples_dir, filename)
        templates[name] = cv2.imread(path, 0)
    return templates

def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def detect_icons(image, templates, threshold=0.7):
    preprocessed = preprocess_image(image)
    detected_icons = []
    for icon_name, template in templates.items():
        res = cv2.matchTemplate(preprocessed, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        for pt in zip(*loc[::-1]):
            detected_icons.append((icon_name, pt, template.shape))
    return detected_icons

def extract_number(image, x, y, w, h):
    number_roi = image[y+int(h*0.6):y+h, x+int(w*0.6):x+w]
    gray = cv2.cvtColor(number_roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((2,2),np.uint8)
    thresh = cv2.dilate(thresh, kernel, iterations=1)
    number = pytesseract.image_to_string(thresh, config='--psm 7 --oem 3 -c tessedit_char_whitelist=x0123456789')
    return ''.join(filter(str.isdigit, number)), thresh

async def process_image(attachment):
    image_data = await attachment.read()
    image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
    
    templates = load_icon_templates()
    detected_icons = detect_icons(image, templates, threshold=0.7)
    
    results = {'3h': 0, '1h': 0, '30m': 0, '5m': 0}
    debug_images = []
    
    # 検出されたアイコンを可視化
    debug_image = image.copy()
    for icon_name, (x, y), (h, w) in detected_icons:
        cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
        number, number_thresh = extract_number(image, x, y, w, h)
        cv2.putText(debug_image, f"{icon_name}: {number}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        if number:
            results[icon_name] += int(number)
        
        # 数字認識用の画像を保存
        debug_images.append((f"{icon_name}_{x}_{y}.png", number_thresh))
    
    # デバッグ画像を一時ファイルとして保存
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
        cv2.imwrite(temp_file.name, debug_image)
        debug_image_path = temp_file.name
    
    return results, debug_image_path, debug_images

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
                    results, debug_image_path, debug_images = await process_image(attachment)
                    total_time = calculate_total_time(results)
                    
                    response = "検出されたアイコンと数量:\n"
                    for icon in ['3h', '1h', '30m', '5m']:
                        response += f"{icon}: {results[icon]}個\n"
                    
                    response += f"\n計算結果: {results['3h']} * 3 + {results['1h']} + {results['30m']} * 0.5 + {results['5m']} / 12 = {total_time:.2f}\n"
                    response += f"合計 {total_time:.2f} 時間"
                    
                    await message.reply(response, file=discord.File(debug_image_path))
                    
                    # 数字認識用の画像を送信
                    for filename, img in debug_images:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                            cv2.imwrite(temp_file.name, img)
                            await message.reply(file=discord.File(temp_file.name, filename=filename))
                    
                except Exception as e:
                    await message.reply(f'画像の処理中にエラーが発生しました: {str(e)}')
                break

    await bot.process_commands(message)

TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)