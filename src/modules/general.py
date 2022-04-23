import datetime
import typing

import discord
from discord.ext import commands

import config
import database
import utils


class GeneralCommands(commands.Cog, name="General"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="donate")
    async def donate(self, ctx):
        """
        Donate to this bot UwU
        """
        await ctx.send(
            "Please go to this site to donate: https://www.patreon.com/RandomGhost (PayPal only).\n"
            "I also accept Bitcoin and other crypto payments. Please contact me (RandomGhost#0666) "
            f"or on the support server (`{ctx.prefix}support`) for other payment methods.\n"
            "Thanks! <a:thanks:699004469610020964>"
        )

    @commands.command(name="invite", aliases=["invitelink"])
    async def invite_bot(self, ctx):
        """
        Get the invite link for the bot's support server
        """
        await ctx.send(
            "Bot invite link: https://top.gg/bot/506878658607054849 <:uwu:575372762583924757>"
        )

    @commands.command(name="creator", aliases=["support"])
    async def creator(self, ctx):
        """
        Get to know the creator of this bot,
        so you can annoy him to fix the damn bugs!
        """
        dev1 = ctx.bot.get_user(252297314394308608) or await ctx.bot.fetch_user(252297314394308608)
        dev2 = ctx.bot.get_user(532123382280355860) or await ctx.bot.fetch_user(532123382280355860)
        await ctx.send(
            f"Bot created by {dev1} and co-developed by {dev2}.\n"
            "Ask them for new features/bugs! <a:thanks:699004469610020964>\n"
            "To join support server, use `=help` or go to https://support.pinocchiobot.xyz."
        )

    @commands.command(name="vote", enabled=(config.DBL_TOKEN is not None))
    async def vote_bot(self, ctx):
        """
        Vote for this bot! Isn't Pinocchio kawaii!?!
        Vote for her and make her happy
        """
        await ctx.send(
            f"Vote for this bot and then claim your reward with `{ctx.prefix}claimreward`!\n"
            "**Vote URL:** https://top.gg/bot/506878658607054849/vote\n"
            "You can vote once every 12 hours. "
            "You get 2x rewards for voting on weekends.\n"
        )

    @commands.command(name="poll")
    async def poll(self, ctx, title: str, *options):
        """
        Create a reaction poll
        """

        if len(options) < 2:
            return await ctx.send("Please add atleast 2 options!")

        if len(options) > 10:
            return await ctx.send("Max 10 options!")

        desc = ""
        for i, opt in enumerate(options):
            desc += ":{0}: : {1}\n".format(utils.num_to_emote[i], opt)

        embed = discord.Embed(title=title, color=ctx.author.color, description=desc)
        embed.set_footer(
            text=f"Poll made by: {ctx.author}",
            icon_url=ctx.author.avatar_url,
        )
        msg = await ctx.send(embed=embed)

        for i, _ in enumerate(options):
            await msg.add_reaction(utils.num_to_uni_emote[i])

    @commands.command(name="whois")
    async def whois(self, ctx, user: typing.Optional[discord.Member]):
        """
        Get information about a user
        """
        user = user or ctx.author

        embed = discord.Embed(title=f"{user.name}#{user.discriminator}", color=user.colour)
        tdelta = datetime.datetime.now() - user.joined_at
        embed.add_field(name="User ID", value=user.id)
        if user.nick:
            embed.add_field(name="Nickname", value=user.nick)
        if user.top_role:
            embed.add_field(name="Top Role", value=user.top_role)
        embed.add_field(name="Status", value=user.status)
        embed.add_field(name="Is Bot", value=user.bot)
        _perms = user.guild_permissions
        embed.add_field(name="Is Administrator", value=_perms.administrator)
        roles = user.roles[1:]
        if len(roles) > 0:
            role_str = ", ".join([i.name for i in roles])
        else:
            role_str = "No roles set."
        embed.add_field(name="Roles", inline=False, value=role_str)
        embed.add_field(
            name="Account Created On",
            inline=False,
            value=discord.utils.snowflake_time(user.id).strftime("%A, %d %B, %Y. %I:%M:%S %p"),
        )
        embed.add_field(
            name="In Server For",
            inline=False,
            value=f"{tdelta.days} days, {tdelta.seconds//3600} hours",
        )
        perms_list = [
            "kick_members",
            "ban_members",
            "manage_channels",
            "manage_guild",
            "add_reactions",
            "view_audit_log",
            "priority_speaker",
            "send_messages",
            "send_tts_messages",
            "manage_messages",
            "attach_files",
            "read_message_history",
            "mention_everyone",
            "embed_links",
            "external_emojis",
            "connect",
            "speak",
            "mute_members",
            "deafen_members",
            "move_members",
            "use_voice_activation",
            "change_nickname",
            "manage_nicknames",
            "manage_roles",
            "manage_webhooks",
            "manage_emojis",
        ]
        perms = []
        for i in perms_list:
            if getattr(_perms, i):
                perms += [i.replace("_", " ").capitalize()]
        if perms == []:
            perms = ["No special permissions."]
        perms_str = ", ".join(perms)
        embed.add_field(name="Permissions", value=perms_str, inline=False)
        embed.set_thumbnail(url=user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(name="say")
    async def say(self, ctx, channel: typing.Optional[discord.TextChannel], *, text: str):
        """
        Speak as Pinocchio.
        """
        channel = channel or ctx.channel

        if not channel.permissions_for(ctx.author).send_messages:
            return await ctx.send(
                "You don't have the permissions to send messages in that channel!"
            )

        if not channel.permissions_for(ctx.author).mention_everyone:
            text = discord.utils.escape_mentions(text)

        await channel.send(text)

    @commands.command(name="worldleaderboard", aliases=["wlb"])
    async def world_leaderboard(self, ctx):
        """
        View the world's leaderboard
        """
        engine = await database.prepare_engine()
        query = """
SELECT id,M.member,tier,COALESCE(wsum,0) as waifu_sum,wallet,(COALESCE(wsum, 0)+wallet) as total
FROM members M
LEFT JOIN (select member_id, sum(purchased_for) as wsum from purchased_waifu group by member_id) PW
ON (M.id = PW.member_id)
WHERE wallet > 0 OR COALESCE(wsum, 0) > 0
ORDER BY total DESC LIMIT 50;
        """
        results = await engine.fetch_all(query=query)
        txt = generate_leaderboard_text(ctx.bot, results)
        embed = discord.Embed(
            title=":trophy: World Leaderboards",
            colour=ctx.author.color,
            description=txt,
        )
        top_user_name = ""
        for result in results:
            top_user = ctx.bot.get_user(result["member"])
            if top_user is not None:
                top_user_name = top_user.name
                break
        embed.set_footer(
            text=f"Current World Champion is {top_user_name}.",
        )
        await ctx.send(embed=embed)

    @commands.command(name="guildleaderboard", aliases=["glb"])
    @utils.ensure_bot_ready()
    async def guild_leaderboard(self, ctx):
        """
        View this guild's leaderboard
        """
        engine = await database.prepare_engine()
        mlist = tuple([m.id for m in ctx.guild.members])
        query = f"""
SELECT id,M.member,tier,COALESCE(wsum,0) as waifu_sum,wallet,(COALESCE(wsum, 0)+wallet) as total
FROM members M LEFT JOIN (
SELECT member_id,sum(purchased_for) as wsum FROM purchased_waifu
WHERE guild = {ctx.guild.id} GROUP BY member_id) PW ON (M.id = PW.member_id)
WHERE (wallet > 0 OR COALESCE(wsum, 0) > 0) AND M.member in {mlist}
ORDER BY total DESC LIMIT 10;
        """
        results = await engine.fetch_all(query=query)
        txt = generate_leaderboard_text(ctx.bot, results)
        embed = discord.Embed(
            title=":trophy: Guild Leaderboards",
            colour=ctx.author.color,
            description=txt,
        )
        top_user_name = ""
        for result in results:
            top_user = ctx.bot.get_user(result["member"])
            if top_user is not None:
                top_user_name = top_user.name
                break
        embed.set_footer(
            text=f"Current Guild Champion is {top_user_name}.",
        )
        await ctx.send(embed=embed)


def generate_leaderboard_text(client, results):
    rtxt = []
    i = 1
    for j in results:
        user = client.get_user(j["member"])
        if user is None:
            continue
        if i <= 3:
            medal = ""
            if i == 1:
                medal = ":first_place:"
            elif i == 2:
                medal = ":second_place:"
            elif i == 3:
                medal = ":third_place:"
            rtxt.append(
                f"**[{str(i).zfill(2)}] __{user.name}__ {medal}**\nWallet: "
                f"{j['wallet']}, Waifu Value: {j['waifu_sum']}, **Total: {j['total']}**"
            )  # noqa
        else:
            rtxt.append(
                f"**[{str(i).zfill(2)}] {user.name}**\nWallet: {j['wallet']}, "
                f"Waifu Value: {j['waifu_sum']}, **Total: {j['total']}**"
            )  # noqa
        i += 1
        if i == 11:
            break
    return "\n".join(rtxt)
