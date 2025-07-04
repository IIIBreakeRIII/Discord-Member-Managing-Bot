from discord.ext import commands
from discord import app_commands, User
from db.mongo import update_user_voice_log, get_last_active_by_user_id, format_korean_datetime_string, add_voice_duration
from datetime import datetime, timezone

import discord

class VoiceTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_times = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        now = datetime.now(timezone.utc)
        user_id = str(member.id)
        username = member.name
        
        # Voice Channel Enter
        if before.channel is None and after.channel is not None:
            self.voice_times[user_id] = now
            print(f"[JOIN] {username} joined {after.channel.name} at {now}")
            await update_user_voice_log(user_id, username=username, join_time=now, channel=after.channel.name)
        
        # Voice Channel Quit
        elif before.channel is not None and after.channel is None:
            join_time = self.voice_times.get(user_id)
            if join_time:
                duration = int((now - join_time).total_seconds())
                print(f"[LEAVE] {username} left {before.channel.name} at {now} (duration: {duration})")
                await add_voice_duration(str(member.id), member.name, duration)
                await update_user_voice_log(user_id, username=username, leave_time=now)
                del self.voice_times[user_id]
        
        # Voice Channel Change
        elif before.channel != after.channel:
            self.voice_times[user_id] = now
            print(f"[MOVE] {username} moved to {after.channel.name} at {now}")
            await update_user_voice_log(user_id, username=username, join_time=now, channel=after.channel.name)

    @app_commands.command(name="출석-확인", description="닉네임 기준으로 마지막 음성 채널 접속시간을 확인합니다.")
    async def attendance_check(self, interaction: discord.Interaction, user: User):
        await interaction.response.defer(thinking=True)
        user_id = str(user.id)
        username = user.name

        last_active = await get_last_active_by_user_id(user_id)
        if last_active:
            formatted_time = format_korean_datetime_string(last_active)
            embed = discord.Embed(
                title="✅ 출석 확인",
                description=f"**`{user.display_name}`** 님의 마지막 접속 시간은\n**`{formatted_time}`** 입니다.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ 출석 기록 없음",
                description=f"**`{user.display_name}`** 님의 접속 기록이 없습니다.",
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=embed)

# 🔑 비동기 setup 함수 (필수!)
async def setup(bot):
    await bot.add_cog(VoiceTracker(bot))
    print("🔌 VoiceTracker Cog loaded")
