import discord
import os
import dotenv
import asyncio
from fastapi import FastAPI
import uvicorn

# FastAPIアプリケーション設定
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Server is Online."}

async def start_server():
    """FastAPIサーバーを非同期タスクとして起動"""
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    server = uvicorn.Server(config)
    await server.serve()

# Discordボット設定
dotenv.load_dotenv()
TOKEN = os.environ.get("TOKEN")

# 特権インテント設定
intents = discord.Intents.default()
intents.message_content = True  # メッセージ内容取得
intents.members = True          # サーバーメンバー情報取得（特権インテント）
intents.presences = True        # ユーザーのプレゼンス情報取得（特権インテント）

client = discord.Client(intents=intents)

debts = {}

@client.event
async def on_ready():
    print(f"Bot {client.user} が起動しました！")

@client.event
async def on_message(message):
    try:
        if message.author == client.user:
            return

        if message.content.startswith('$hello'):
            await message.channel.send('Hello!')

        if message.content.startswith('/borrow'):
            try:
                amount = float(message.content.split()[1])
                if message.author.id not in debts:
                    debts[message.author.id] = 0
                debts[message.author.id] += amount
                await message.channel.send(f'あなたは {amount} 円を借りました。総借金: {debts[message.author.id]} 円')
            except (IndexError, ValueError):
                await message.channel.send('使用法: /borrow [金額]')

        if message.content.startswith('/interest'):
            try:
                rate = float(message.content.split()[1])
                if rate < 0:
                    await message.channel.send('利率は正の値で指定してください。')
                    return
                if message.author.id in debts:
                    interest = debts[message.author.id] * (rate / 100)
                    await message.channel.send(f'毎月の利子: {interest} 円')
                else:
                    await message.channel.send('借金がありません。')
            except (IndexError, ValueError):
                await message.channel.send('使用法: /interest [利率]')

        if message.content.startswith('/total'):
            if message.author.id in debts:
                await message.channel.send(f'総借金: {debts[message.author.id]} 円')
            else:
                await message.channel.send('借金がありません。')
    except Exception as e:
        await message.channel.send(f"エラーが発生しました: {e}")

# メイン関数で非同期タスクとして実行
async def main():
    asyncio.create_task(start_server())  # FastAPIサーバー起動
    await client.start(TOKEN)           # Discordボット起動

if __name__ == "__main__":
    asyncio.run(main())
