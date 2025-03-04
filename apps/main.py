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
        self.debts = {}  # 借金データ: {借り主ID: {貸し主ID: 現在の借金額}}
        self.initial_debts = {}  # 初期借金データ: {借り主ID: {貸し主ID: 初期の借金額}}
        self.interests = {}  # 利子データ: {借り主ID: {貸し主ID: 利子}}
        self.interest_rates = {}  # 利率データ: {借り主ID: {貸し主ID: 利率}}

    async def setup_hook(self):
        await self.tree.sync()

client = InterestBot(intents=intents)

# スラッシュコマンド: /borrow
@client.tree.command(name="borrow", description="誰からいくら借りたかを記録します")
async def borrow(interaction: discord.Interaction, amount: float, lender: discord.Member):
    if interaction.user.id == lender.id:
        await interaction.response.send_message("エラー: 自分自身から借りることはできません。", ephemeral=True)
        return

    borrower_id = interaction.user.id
    lender_id = lender.id

    # 借金データの更新
    if borrower_id not in client.debts:
        client.debts[borrower_id] = {}
    if lender_id not in client.debts[borrower_id]:
        client.debts[borrower_id][lender_id] = 0
    client.debts[borrower_id][lender_id] += amount

    # 初期借金データの設定（初回のみ）
    if borrower_id not in client.initial_debts:
        client.initial_debts[borrower_id] = {}
    if lender_id not in client.initial_debts[borrower_id]:
        client.initial_debts[borrower_id][lender_id] = amount

    embed = discord.Embed(
        title="借金記録",
        description=f"{interaction.user.name} が {lender.name} から {amount} 円借りました。",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# スラッシュコマンド: /interest
@client.tree.command(name="interest", description="誰からの利子金額を設定します")
async def interest(interaction: discord.Interaction, lender: discord.Member, rate: float):
    if interaction.user.id == lender.id:
        await interaction.response.send_message("エラー: 自分自身に利子を設定することはできません。", ephemeral=True)
        return

    borrower_id = interaction.user.id
    lender_id = lender.id

    if rate < 0:
        await interaction.response.send_message("エラー: 利率は正の値で指定してください。", ephemeral=True)
        return

    if borrower_id in client.debts and lender_id in client.debts[borrower_id]:
        # 利率データの設定
        if borrower_id not in client.interest_rates:
            client.interest_rates[borrower_id] = {}
        client.interest_rates[borrower_id][lender_id] = rate

        # 初期借金額を基準に利子計算
        initial_debt_amount = client.initial_debts[borrower_id][lender_id]
        interest_amount = initial_debt_amount * (rate / 100)

        if borrower_id not in client.interests:
            client.interests[borrower_id] = {}
        client.interests[borrower_id][lender_id] = interest_amount

        embed = discord.Embed(
            title="利子設定",
            description=f"{interaction.user.name} の {lender.name} に対する利率を {rate}% に設定しました。\n"
                        f"元の借金額（固定）: {initial_debt_amount} 円\n"
                        f"毎月の利子額（固定）: {interest_amount} 円",
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
            description=f"総借金額（現在）: {total_debt} 円\n"
                        f"総利子額（固定）: {total_interest} 円\n"
                        f"総合計額（現在 + 利子）: {total_amount} 円",
            color=discord.Color.purple()
        )

        # 詳細情報を追加
        for lender_id, debt in client.debts[borrower_id].items():
            interest_amount = client.interests.get(borrower_id, {}).get(lender_id, 0)
            lender_user = await client.fetch_user(lender_id)
            embed.add_field(
                name=f"{lender_user.name} からの詳細",
                value=f"現在の借金額: {debt} 円\n"
                      f"毎月の利子額（固定）: {interest_amount} 円\n"
                      f"合計（現在 + 利子）: {debt + interest_amount} 円",
                inline=False
            )

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("現在、記録された借金がありません。")

# 月初めに利率更新とアナウンス
async def monthly_update():
    while True:
        now = datetime.now()
        next_month_start = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        wait_time = (next_month_start - now).total_seconds()

        await asyncio.sleep(wait_time)

        for borrower, lenders in client.debts.items():
            for lender, debt in lenders.items():
                # 初期値で固定された毎月の利子額を再通知
                initial_debt_amount = client.initial_debts[borrower][lender]
                current_rate = client.interest_rates.get(borrower, {}).get(lender, 0)
                interest_amount = initial_debt_amount * (current_rate / 100)

                user_borrower = await client.fetch_user(borrower)
                user_lender = await client.fetch_user(lender)

                embed = discord.Embed(
                    title="月初め更新",
                    description=f"{user_borrower.name} の新しい借金情報:\n"
                                f"元の借金額（固定）: {initial_debt_amount} 円\n"
                                f"現在の利率（固定）: {current_rate}%\n"
                                f"毎月の利子額（固定）: {interest_amount} 円",
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
