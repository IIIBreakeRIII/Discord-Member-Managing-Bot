from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db.mongo import collection, format_korean_datetime_string, format_kst
from datetime import datetime, timezone, timedelta
from apscheduler.triggers.cron import CronTrigger

import discord
import pytz

CHANNEL_ID = 1111111111111111111  # 알림을 보낼 채널 ID

ROLE_MASTER = "<@&1111111111111111111>"     # 역할 ID
ROLE_ORGANIZER = "<@&1111111111111111111>"  # 역할 ID

class AttendanceAlert(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(
            self.check_attendance,
            trigger=CronTrigger(hour=12, minute=0, timezone='Asia/Seoul')
        )
        self.scheduler.start()

    async def check_attendance(self):
        # 현재 시각을 KST 문자열로 생성
        now_kst_str = format_kst(datetime.now(timezone.utc))
        print(f"[AttendanceAlert] 출석 체크 실행됨: {now_kst_str}")
        async for user in collection.find({}):
            user_id = user.get("user_id")
            username = user.get("username", "알 수 없음")
            last_active_str = user.get("last_active")
            if not last_active_str:
                joined_at = user.get("joined_at_server", None)
                if not joined_at:
                    continue  # 입장 시간도 없으면 스킵
                try:
                    now_kst = datetime.strptime(now_kst_str, "%Y-%m-%dT%H-%M-%S")
                    joined_at_kst = datetime.strptime(joined_at, "%Y-%m-%dT%H-%M-%S")
                except Exception as e:
                    continue
                days_inactive = (now_kst - joined_at_kst).days
                if days_inactive == 14 or days_inactive == 30:
                    guilds = self.bot.guilds
                    for guild in guilds:
                        member = guild.get_member(int(user_id))
                        if member:
                            channel = guild.get_channel(CHANNEL_ID)
                            if channel:
                                joined_at_kor = format_korean_datetime_string(joined_at)
                                embed = discord.Embed(
                                    title="⚠️ 접속 기록 없음 안내",
                                    description=(
                                        f"{ROLE_MASTER} {ROLE_ORGANIZER}\n"
                                        f"**{member.mention}** 님은 접속 기록이 아직 없습니다!\n"
                                        f"서버 입장 시간은 `{joined_at_kor}` 입니다.\n"
                                        f"{days_inactive}일 동안 접속 기록이 없습니다!"
                                    ),
                                    color=discord.Color.red()
                                )
                                await channel.send(embed=embed)
                continue
            try:
                # KST 문자열을 naive datetime으로 파싱
                now_kst = datetime.strptime(now_kst_str, "%Y-%m-%dT%H-%M-%S")
                last_active_kst = datetime.strptime(last_active_str, "%Y-%m-%dT%H-%M-%S")
            except Exception as e:
                continue
            seconds_inactive = (now_kst - last_active_kst).total_seconds()
            days_inactive = (now_kst - last_active_kst).days
            if days_inactive == 14 or days_inactive == 30:
                guilds = self.bot.guilds
                for guild in guilds:
                    member = guild.get_member(int(user_id))
                    if member:
                        channel = guild.get_channel(CHANNEL_ID)
                        if channel:
                            last_active_kor = format_korean_datetime_string(last_active_str)
                            embed = discord.Embed(
                                title="⚠️ 장기 미접속 안내",
                                description=(
                                    f"{ROLE_MASTER} {ROLE_ORGANIZER}\n"
                                    f"**{member.mention}** 님은 마지막 접속일이 `{last_active_kor}` 입니다.\n"
                                    f"{days_inactive}일 동안 접속하지 않았습니다!"
                                ),
                                color=discord.Color.red()
                            )
                            await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AttendanceAlert(bot))
    print("⏰[Background Cog] AttendanceAlert Cog loaded")
