import discord
import os
import dotenv
import asyncio
import logging
from fastapi import FastAPI
import uvicorn
from datetime import datetime, timedelta

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
TOKEN = os.getenv("TOKEN")

# 特権インテント設定
intents = discord.Intents.default()
intents.message_content = True  # メッセージ内容取得

class InterestBot(discord.Client):
    def __init__(self, intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.debts = {}  # 借金データ: {借り主ID: {貸し主ID: 金額}}
        self.interests = {}  # 利子データ: {借り主ID: {貸し主ID: 利子}}

    async def setup_hook(self):
        await self.tree.sync()

client = InterestBot(intents=intents)

# スラッシュコマンド: /borrow
@client.tree.command(name="borrow", description="誰からいくら借りたかを記録します")
async def borrow(interaction: discord.Interaction, amount: float, lender: discord.Member):
    borrower_id = interaction.user.id
    lender_id = lender.id

    if borrower_id not in client.debts:
        client.debts[borrower_id] = {}
    if lender_id not in client.debts[borrower_id]:
        client.debts[borrower_id][lender_id] = 0

    client.debts[borrower_id][lender_id] += amount

    embed = discord.Embed(
        title="借金記録",
        description=f"{interaction.user.name} が {lender.name} から {amount} 円借りました。",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# スラッシュコマンド: /interest
@client.tree.command(name="interest", description="利子と送金額を計算します")
async def interest(interaction: discord.Interaction, rate: float, lender: discord.Member):
    borrower_id = interaction.user.id
    lender_id = lender.id

    if rate < 0:
        await interaction.response.send_message("利率は正の値で指定してください。")
        return

    if borrower_id in client.debts and lender_id in client.debts[borrower_id]:
        debt_amount = client.debts[borrower_id][lender_id]
        interest_amount = debt_amount * (rate / 100)

        if borrower_id not in client.interests:
            client.interests[borrower_id] = {}
        client.interests[borrower_id][lender_id] = interest_amount

        embed = discord.Embed(
            title="利子計算",
            description=f"{interaction.user.name} の毎月の利子: {interest_amount} 円\n"
                        f"元の借金額: {debt_amount} 円",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("指定された貸し主からの借金がありません。")

# スラッシュコマンド: /total
@client.tree.command(name="total", description="合計利子と借金を表示します")
async def total(interaction: discord.Interaction):
    borrower_id = interaction.user.id

    if borrower_id in client.debts:
        total_debt = sum(client.debts[borrower_id].values())
        total_interest = sum(client.interests.get(borrower_id, {}).values())
        total_amount = total_debt + total_interest

        embed = discord.Embed(
            title="総合計",
            description=f"総借金額: {total_debt} 円\n"
                        f"総利子額: {total_interest} 円\n"
                        f"総合計額: {total_amount} 円",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("現在、記録された借金がありません。")

# スラッシュコマンド: /return
@client.tree.command(name="return", description="返済額を記録します")
async def return_debt(interaction: discord.Interaction, amount: float, lender: discord.Member):
    borrower_id = interaction.user.id
    lender_id = lender.id

    if borrower_id in client.debts and lender_id in client.debts[borrower_id]:
        client.debts[borrower_id][lender_id] -= amount

        if client.debts[borrower_id][lender_id] <= 0:
            del client.debts[borrower_id][lender_id]

        embed = discord.Embed(
            title="返済記録",
            description=f"{interaction.user.name} が {lender.name} に {amount} 円返済しました。",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("指定された貸し主への借金がありません。")

# 月初めに利子更新とアナウンス
async def monthly_update():
    while True:
        now = datetime.now()
        next_month_start = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        wait_time = (next_month_start - now).total_seconds()

        await asyncio.sleep(wait_time)

        for borrower, lenders in client.debts.items():
            for lender, debt in lenders.items():
                interest_amount = client.interests.get(borrower, {}).get(lender, 0)
                new_total_debt = debt + interest_amount

                user_borrower = await client.fetch_user(borrower)
                user_lender = await client.fetch_user(lender)

                embed = discord.Embed(
                    title="月初め更新",
                    description=f"{user_borrower.name} の新しい借金額:\n"
                                f"元の借金額: {debt} 円\n"
                                f"加算された利子額: {interest_amount} 円\n"
                                f"合計借金額: {new_total_debt} 円",
                    color=discord.Color.red()
                )

                # アナウンス（ここではDM送信）
                await user_borrower.send(embed=embed)

# メイン関数で非同期タスクとして実行
async def main():
    asyncio.create_task(start_server())  # FastAPIサーバー起動
    asyncio.create_task(monthly_update())  # 月初め更新タスク起動
    await client.start(TOKEN)           # Discordボット起動

if __name__ == "__main__":
    asyncio.run(main())
