import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む（ローカル開発用）
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました')

@bot.command()
async def hello(ctx):
    await ctx.send('こんにちは！')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                await message.channel.send('画像を確認した！')
                break  # 複数の画像がある場合、最初の1つにのみ反応

    await bot.process_commands(message)

# 環境変数からトークンを取得
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)