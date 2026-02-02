from discord.ext import commands
from discord import app_commands, Interaction
import discord
from db.mongo import upsert_member_info
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cogs import is_master_or_organizer_appcmd
from settings import ALERT_CHANNEL_ID, ROLE_MASTER_MENTION, ROLE_ORGANIZER_MENTION
from utils.logging_utils import log_bot

class ServerSynchronization(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(self.auto_sync_server_members, 'interval', days=7)
        self.scheduler.start()

    @app_commands.command(name="서버동기화", description="현재 서버에 있는 모든 멤버 정보를 DB와 동기화합니다.")
    @is_master_or_organizer_appcmd()
    async def sync_server_members(self, interaction: Interaction):
        await interaction.response.defer(thinking=True)
        await self._sync_members(interaction.guild, interaction)

    async def auto_sync_server_members(self):
        for guild in self.bot.guilds:
            updated = await self._sync_members(guild)
            # 동기화 후 메시지 전송
            channel = guild.get_channel(ALERT_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="🔁 서버 멤버 주간 동기화 완료",
                    description=f"{ROLE_MASTER_MENTION} {ROLE_ORGANIZER_MENTION}\n✅ 총 `{updated}`명의 멤버 정보를 동기화했습니다.",
                    color=discord.Color.teal()
                )
                await channel.send(embed=embed)

    async def _sync_members(self, guild, interaction=None):
        if not guild:
            if interaction:
                await interaction.followup.send("❌ 서버 정보를 가져올 수 없습니다.")
            return 0
        
        updated = 0
        async for member in guild.fetch_members(limit=None):
            if member.bot:
                continue  # 봇은 제외

            data = {
                "user_id": str(member.id),
                "username": member.name,
                "server_nickname": member.display_name,
                "joined_at_server": member.joined_at.isoformat() if member.joined_at else None,
                "granted_role": [r.name for r in member.roles if not r.is_default()],
            }

            log_id = log_bot("DB Writing", f"sync member info: {member.name}")
            await upsert_member_info(data, log_id=log_id)
            updated += 1

        if interaction:
            embed = discord.Embed(
                    title="🔁 서버 멤버 수동 동기화 완료",
                    description=f"✅ 총 `{updated}`명의 멤버 정보를 동기화했습니다.",
                    color=discord.Color.teal()
            )
            await interaction.followup.send(embed=embed)

        return updated

async def setup(bot):
    await bot.add_cog(ServerSynchronization(bot))
    log_bot("Load Complete", "ServerSynchronization Cog loaded")
