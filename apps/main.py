import discord
import os
import dotenv

from server import server_thread

dotenv.load_dotenv()

TOKEN = os.environ.get("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
client = discord.Client(intents=intents)

debts = {}

@client.event
async def on_message(message):
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

# Koyeb用 サーバー立ち上げ
server_thread()
client.run(TOKEN)