# main.py

import os
import discord

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s).")
    except Exception as e:
        print("❌ Slash command sync failed:", e)

async def main():
    # Cog 비동기 로드
    await bot.load_extension("cogs.voice_tracker")
    await bot.load_extension("cogs.grant_authority")
    await bot.load_extension("cogs.server_join_time")
    await bot.load_extension("cogs.user_profile_tracker")
    await bot.load_extension("cogs.voice_duration_tracker")
    await bot.load_extension("cogs.server_synchronization")
    
    # Prod v2.0
    # 퇴장 시간 기록 추적
    await bot.load_extension("cogs.rejoin_tracker")
    # 출석 알림
    await bot.load_extension("cogs.attendance_alert")

    await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
