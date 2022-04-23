import discord
from discord.ext import commands


class CustomHelpCommand(commands.DefaultHelpCommand):
    cog_fancy_name = {
        "General": ":robot: General",
        "Financial": ":moneybag: Financial",
        "Waifu": "<a:RainbowWeeb:564012559590752256> Waifu",
        "Anime": "<:UmaruCool:575381825296400384> Anime",
        "Quiz": "<:SmartHuh:575382892520275980> Quiz",
        "Fun": "<a:MikuKurukurupa:564012084631699456> Fun",
        "Reactions": "<a:PKomiEars:575382520179326979> Reactions",
        "Admin": ":tools: Administration",
        "Developer": ":gear: Developer",
    }

    # This function triggers when somone type `<prefix>help`
    async def send_bot_help(self, mapping):
        ctx = self.context

        embed = discord.Embed(
            title="Pinocchio Bot Usage",
            description=f"""
        **Support Server: https://support.pinocchiobot.xyz**
        **For additional help, do `{self.clean_prefix}help <command name or category name>`.**
            """,
        )
        for cog, raw_cmds in mapping.items():
            cmds = await self.filter_commands(raw_cmds, sort=True)
            if len(cmds) == 0:
                continue
            cog_name = cog.qualified_name if cog is not None else "Default"
            cog_name = self.cog_fancy_name.get(cog_name, cog_name)
            embed.add_field(
                name=cog_name,
                value=", ".join([f"`{self.clean_prefix}{c.qualified_name}`" for c in cmds]),
                inline=False,
            )
        embed.set_footer(text=f"For additional help, do {self.clean_prefix}help <command name>")

        await ctx.send(embed=embed)

    # # This function triggers when someone type `<prefix>help <cog>`
    # async def send_cog_help(self, cog):
    #     ctx = self.context

    # # This function triggers when someone type `<prefix>help <command>`
    # async def send_command_help(self, command):
    #     ctx = self.context

    # # This function triggers when someone type `<prefix>help <group>`
    # async def send_group_help(self, group):
    #     ctx = self.context


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Storing main help command in a variable
        self.bot.original_help_command = bot.help_command

        # Assiginig new help command to bot help command
        bot.help_command = CustomHelpCommand(command_attrs={"hidden": True})

        # Setting this cog as help command cog
        bot.help_command.cog = self

    # Event triggers when this cog unloads
    def cog_unload(self):
        self.bot.help_command = self.bot.original_help_command
