import discord
import os
import io
from discord.ext import commands
from dotenv import load_dotenv
import pytesseract
from PIL import Image

# .envファイルから環境変数を読み込む（ローカル開発用）
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました')
    print(f'ボットは以下のサーバーに参加しています:')
    for guild in bot.guilds:
        print(f'- {guild.name} (id: {guild.id})')

@bot.command()
async def hello(ctx):
    await ctx.send('こんにちは！')

async def process_image(attachment):
    image_data = await attachment.read()
    image = Image.open(io.BytesIO(image_data))
    text = pytesseract.image_to_string(image, lang='jpn')
    return text

@bot.event
async def on_message(message):
    print(f'メッセージを受信: {message.content} from {message.author}')
    if message.author == bot.user:
        return

    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                await message.reply('画像を処理中...')
                text = await process_image(attachment)
                await message.reply(f'抽出されたテキスト:\n```\n{text}\n```')
                print(f'画像を処理: {attachment.filename}')
                break  # 複数の画像がある場合、最初の1つにのみ反応

    await bot.process_commands(message)

# 環境変数からトークンを取得
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)