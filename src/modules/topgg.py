import logging

import dbl
import discord
from discord.ext import commands, tasks

import config


class TopGGCog(commands.Cog):
    def __init__(self, bot, dbl_token):
        self.bot = bot
        self.token = dbl_token
        self.dblpy = dbl.DBLClient(self.bot, self.token)

        self.auto_update_stats.start()  # pylint: disable=no-member

    def cog_unload(self):
        self.auto_update_stats.stop()  # pylint: disable=no-member

    @tasks.loop(minutes=10.0)
    async def auto_update_stats(self):
        await self._update_stats()

    async def _update_stats(self):
        logging.info("Attempting to post server count")
        try:
            await self.dblpy.post_guild_count()
            logging.info("Posted server count (%d)", self.dblpy.guild_count())
            activity = discord.Game(
                name=f"{config.PREFIX}help | Playing around in {self.dblpy.guild_count()} servers"
            )
            await self.bot.change_presence(activity=activity)
        except Exception as err:  # pylint: disable=broad-except
            logging.exception("Failed to post server count\n%s: %s", type(err).__name__, err)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self._update_stats()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self._update_stats()
