import discord
import os
import io
from discord.ext import commands
from dotenv import load_dotenv
import pytesseract
from PIL import Image
import cv2
import numpy as np

pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました')

def preprocess_image(image):
    # グレースケールに変換
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # ノイズ除去
    denoised = cv2.fastNlMeansDenoising(gray)
    # 二値化
    _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

def detect_icons(image):
    # ここでアイコンを検出するロジックを実装
    # 例: テンプレートマッチングや機械学習モデルを使用
    # 仮のコード: 画像を4分割して "アイコン" とする
    height, width = image.shape
    icons = [
        image[0:height//2, 0:width//2],
        image[0:height//2, width//2:],
        image[height//2:, 0:width//2],
        image[height//2:, width//2:]
    ]
    return icons

def extract_numbers(icons):
    numbers = []
    for icon in icons:
        # アイコンごとに数字を抽出
        number = pytesseract.image_to_string(icon, config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')
        numbers.append(number.strip())
    return numbers

async def process_image(attachment):
    image_data = await attachment.read()
    image = Image.open(io.BytesIO(image_data))
    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    preprocessed = preprocess_image(opencv_image)
    icons = detect_icons(preprocessed)
    numbers = extract_numbers(icons)
    
    return numbers

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(('.png', '.jpg', '.jpeg')):
                await message.reply('画像を処理中...')
                try:
                    numbers = await process_image(attachment)
                    result = f'検出された数値:\n'
                    for i, number in enumerate(numbers, 1):
                        result += f'アイコン{i}: {number}\n'
                    await message.reply(result)
                except Exception as e:
                    await message.reply(f'画像の処理中にエラーが発生しました: {str(e)}')
                break

    await bot.process_commands(message)

TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)