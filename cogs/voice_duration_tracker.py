from discord.ext import commands
from discord import app_commands, Interaction, User
from db.mongo import get_total_voice_duration
import discord

def format_duration(seconds: int) -> str:
    units = [
        ("년", 60 * 60 * 24 * 365),
        ("일", 60 * 60 * 24),
        ("시간", 60 * 60),
        ("분", 60),
        ("초", 1)
    ]

    parts = []
    for name, unit_seconds in units:
        value, seconds = divmod(seconds, unit_seconds)
        if value > 0 or (name == "초" and not parts):  # 최소 '0초'는 출력
            parts.append(f"{value}{name}")
    return " ".join(parts)

class VoiceDurationTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="음성-리더보드",
        description="해당 유저가 서버 내 음성 채널에서 보낸 총 시간을 계산합니다."
    )
    async def stay_duration(self, interaction: Interaction, user: User):
        await interaction.response.defer(thinking=True)

        total_seconds = await get_total_voice_duration(str(user.id))
        formatted = format_duration(total_seconds or 0)

        embed = discord.Embed(
            title="🎧 음성 리더 보드",
            description=f"✅ **`{user.display_name}`** 님은 음성 채널에서 총 **`{formatted}`** 동안 있었어요.",
            color=discord.Color.purple()
        )
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VoiceDurationTracker(bot))
    print("🕒 VoiceDurationTracker Cog loaded")
