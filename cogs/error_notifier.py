from discord.ext import commands
from discord import app_commands, Interaction
from cogs import is_master_or_organizer_appcmd
from settings import load_config, update_config
from utils.logging_utils import log_bot, set_error_callback


class ErrorNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        set_error_callback(self._handle_error)

    def _handle_error(self, message: str):
        self.bot.loop.create_task(self._send_error(message))

    async def _send_error(self, message: str):
        config = load_config()
        channel_id = config.get("ERROR_CHANNEL_ID")
        if not channel_id:
            return
        try:
            channel_id_int = int(channel_id)
        except ValueError:
            log_bot("Error", "ERROR_CHANNEL_ID is not numeric")
            return
        channel = self.bot.get_channel(channel_id_int)
        if channel:
            await channel.send(message)

    @app_commands.command(name="에러-알림-채널-설정", description="에러 로그를 전송할 채널 ID를 설정합니다.")
    @is_master_or_organizer_appcmd()
    async def set_error_channel(self, interaction: Interaction, channel_id: str):
        update_config("ERROR_CHANNEL_ID", channel_id)
        await interaction.response.send_message(
            f"[Load Complete] ERROR_CHANNEL_ID set to `{channel_id}`",
            ephemeral=True
        )

    @app_commands.command(name="에러-테스트", description="[테스트]에러 로그 전송 테스트를 수행합니다.")
    @is_master_or_organizer_appcmd()
    async def error_test(self, interaction: Interaction):
        log_id = log_bot("Error", "Manual error test")
        await interaction.response.send_message(
            f"[Load Complete] Error test sent (log id: {log_id})",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(ErrorNotifier(bot))
    log_bot("Load Complete", "ErrorNotifier Cog loaded")
