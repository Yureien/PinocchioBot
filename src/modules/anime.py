import datetime
import json
from base64 import b64encode
from io import BytesIO

import aiohttp
import discord
from discord.ext import commands
from jikanpy import AioJikan
from jikanpy.exceptions import APIException
from PIL import Image

import config
import utils


class AnimeCommands(commands.Cog, name="Anime"):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.jikan = AioJikan()
        self.mal_statuses = {
            1: "Currently Watching",
            2: "Completed",
            3: "On Hold",
            4: "Dropped",
            6: "Plan To Watch",
        }
        self.mml_statuses = {
            1: "Currently Reading",
            2: "Completed",
            3: "On Hold",
            4: "Dropped",
            6: "Plan To Read",
        }

    @commands.command(name="anime")
    @utils.typing_indicator()
    async def anime(self, ctx, *, anime_name: str):
        """
        Get details about an anime.
        """
        search_result = await self.jikan.search(search_type="anime", query=anime_name)
        search_result = search_result["results"][0]["mal_id"]
        anime = await self.jikan.anime(search_result)

        embed = make_anime_embed(anime, ctx.author.color)
        await ctx.send(embed=embed)

    @commands.command(name="manga")
    @utils.typing_indicator()
    async def manga(self, ctx, *, manga_name: str):
        """
        Get details about a manga
        """
        search_result = await self.jikan.search(search_type="manga", query=manga_name)
        search_result = search_result["results"][0]["mal_id"]
        manga = await self.jikan.manga(search_result)

        synopsis = manga["synopsis"]
        if len(synopsis) > 1500:
            synopsis = synopsis[:1500] + "..."

        embed = discord.Embed(
            title=manga["title"],
            description=synopsis,
            url=manga["url"],
            color=ctx.author.colour,
        )

        if "image_url" in manga.keys() and manga["image_url"]:
            embed.set_image(url=manga["image_url"])
        embed.add_field(name="Type", value=manga["type"])
        embed.add_field(name="Chapters", value=f"{manga['chapters']} ({manga['volumes']} volumes)")
        embed.add_field(name="Status", value=manga["status"])
        embed.add_field(name="Published", value=manga["published"]["string"])
        embed.add_field(name="Rank", value=manga["rank"])
        embed.add_field(name="Score", value=f"{manga['score']} by {manga['scored_by']} members")
        genres = ", ".join([g["name"] for g in manga["genres"]])
        embed.add_field(name="Genres", value=genres, inline=True)
        if "Adaptation" in manga["related"].keys():
            adaptations = ", ".join(
                [f"{i['name']} ({i['type']})" for i in manga["related"]["Adaptation"]]
            )
            embed.add_field(name="Adaptations", value=adaptations, inline=True)
        embed.set_footer(text="Taken from MyMangaList.net")

        await ctx.send(embed=embed)

    @commands.command(name="myanimelist", aliases=["animelist", "mal"])
    @utils.typing_indicator()
    async def my_anime_list(self, ctx, *, mal_username: str):
        """
        Get someone's animelist
        """
        try:
            raw_animelist = await self.jikan.user(username=mal_username, request="animelist")
        except APIException:
            return await ctx.send(
                "Username not found on MyAnimeList, or account is private.\n"
                "Note that MyAnimeList username may be different from Discord username."
            )

        animelist = raw_animelist["anime"]
        sentences = []
        animelist.sort(key=lambda x: x["score"], reverse=True)
        for i, anime in enumerate(animelist):
            watching_status = anime["watching_status"]
            if watching_status not in self.mal_statuses:
                continue
            status = self.mal_statuses[watching_status]
            if watching_status != 6:
                status += f" ({anime['watched_episodes']}/{anime['total_episodes']} eps)"

            url = anime["url"].replace("_", r"\_")
            sentences.append(
                f"{i + 1}: **__[{anime['title']}]({url})__** ({anime['type']})"
                f"\nStatus: **{status}** | Score: **{anime['score']}**"
            )

        pages = utils.smart_chunks(sentences, 1980)
        total_pages = len(pages)

        embed = discord.Embed(
            title=f"{mal_username}'s Anime List",
            color=ctx.author.color,
            description="\n".join(pages[0]),
        )
        embed.add_field(name="Total Anime", value=len(animelist))
        embed.set_footer(text=f"Page: {1}/{total_pages}")

        async def modifier_func(page_num, **kwargs):
            embed.description = "\n".join(pages[page_num])
            embed.set_footer(text=f"Page: {page_num+1}/{total_pages}")

        await utils.paginate_embed(ctx, embed, len(pages), modifier_func)

    @commands.command(name="mymangalist", aliases=["mangalist", "mml"])
    @utils.typing_indicator()
    async def my_manga_list(self, ctx, *, mal_username: str):
        """
        Get someone's manga list
        """
        try:
            raw_mangalist = await self.jikan.user(username=mal_username, request="mangalist")
        except APIException:
            return await ctx.send(
                "Username not found on MyAnimeList, or account is private.\n"
                "Note that MyAnimeList username may be different from Discord username."
            )

        mangalist = raw_mangalist["manga"]
        sentences = []
        mangalist.sort(key=lambda x: x["score"], reverse=True)
        for i, manga in enumerate(mangalist):
            reading_status = manga["reading_status"]
            if reading_status not in self.mml_statuses:
                continue
            status = self.mml_statuses[reading_status]
            if reading_status != 6:
                status += f" ({manga['read_chapters']}/{manga['total_chapters']} eps)"

            url = manga["url"].replace("_", r"\_")
            sentences.append(
                f"{i + 1}: **__[{manga['title']}]({url})__** ({manga['type']})"
                f"\nStatus: **{status}** | Score: **{manga['score']}**"
            )

        pages = utils.smart_chunks(sentences, 1980)
        total_pages = len(pages)

        embed = discord.Embed(
            title=f"{mal_username}'s Manga List",
            color=ctx.author.color,
            description="\n".join(pages[0]),
        )
        embed.add_field(name="Total Manga", value=len(mangalist))
        embed.set_footer(text=f"Page: {1}/{total_pages}")

        async def modifier_func(page_num, **kwargs):
            embed.description = "\n".join(pages[page_num])
            embed.set_footer(text=f"Page: {page_num+1}/{total_pages}")

        await utils.paginate_embed(ctx, embed, len(pages), modifier_func)

    @commands.command(name="malprofile", aliases=["profile"])
    @utils.typing_indicator()
    async def mal_profile(self, ctx, *, mal_username: str):
        """
        Get someone's MAL profile
        """
        try:
            profile = await self.jikan.user(username=mal_username, request="profile")
        except APIException:
            return await ctx.send(
                "Username not found on MyAnimeList, or account is private.\n"
                "Note that MyAnimeList username may be different from Discord username."
            )

        embed = discord.Embed(
            title=f"{mal_username}'s MAL Profile",
            url=profile["url"],
            color=ctx.author.colour,
        )

        if profile["image_url"]:
            embed.set_thumbnail(url=profile["image_url"])
        if profile["gender"]:
            embed.add_field(name="Gender", value=profile["gender"])
        if profile["birthday"]:
            birthday = datetime.datetime.fromisoformat(profile["birthday"]).strftime(
                "%A, %d %B, %Y"
            )
            embed.add_field(name="Birthday", value=birthday)
        if profile["location"]:
            embed.add_field(name="Location", value=profile["location"])
        if profile["joined"]:
            joined = datetime.datetime.fromisoformat(profile["joined"]).strftime("%A, %d %B, %Y")
            embed.add_field(name="Joined MyAnimeList", value=joined)
        about = profile["about"]
        if about:
            if len(about) > 980:
                about = about[:980] + "..."
            embed.add_field(name="About Them", value=about, inline=False)
        astats = profile["anime_stats"]
        anime_stats = f"""
Days of anime watched: {astats['days_watched']}
Mean score: {astats['mean_score']}
Watching: {astats['watching']}
Completed: {astats['completed']}
On Hold: {astats['on_hold']}
Dropped: {astats['dropped']}
Plan to Watch: {astats['plan_to_watch']}
Rewatched: {astats['rewatched']}
Episodes Watched: {astats['episodes_watched']}
Total: {astats['total_entries']}
        """
        mstats = profile["manga_stats"]
        manga_stats = f"""
Days of manga read: {mstats['days_read']}
Mean score: {mstats['mean_score']}
Reading: {mstats['reading']}
Completed: {mstats['completed']}
On Hold: {mstats['on_hold']}
Dropped: {mstats['dropped']}
Plan to Read: {mstats['plan_to_read']}
Reread: {mstats['reread']}
Chapters Read: {mstats['chapters_read']}
Volumes Read: {mstats['volumes_read']}
Total: {mstats['total_entries']}
        """
        embed.add_field(name="Anime Stats", value=anime_stats)
        embed.add_field(name="Manga Stats", value=manga_stats)
        if profile["favorites"]["anime"]:
            afavs = profile["favorites"]["anime"]
            anime_favorites = ", ".join(
                [
                    "[{0}]({1})".format(i["name"].replace(",", ""), i["url"].replace("_", r"\_"))
                    for i in afavs
                ]
            )
        else:
            anime_favorites = "No anime favorites set."
        if profile["favorites"]["manga"]:
            mfavs = profile["favorites"]["manga"]
            manga_favorites = ", ".join(
                [
                    "[{0}]({1})".format(i["name"].replace(",", ""), i["url"].replace("_", r"\_"))
                    for i in mfavs
                ]
            )
        else:
            manga_favorites = "No manga favorites set."
        if profile["favorites"]["characters"]:
            cfavs = profile["favorites"]["characters"]
            favorite_chars = ", ".join(
                [
                    "[{0}]({1})".format(i["name"].replace(",", ""), i["url"].replace("_", r"\_"))
                    for i in cfavs
                ]
            )
        else:
            favorite_chars = "No favorite characters set."
        embed.add_field(name="Anime Favorites", value=anime_favorites, inline=False)
        embed.add_field(name="Manga Favorites", value=manga_favorites, inline=False)
        embed.add_field(name="Favorite Characters", value=favorite_chars, inline=False)
        await ctx.send(embed=embed)

    @commands.command(
        name="findanime",
        aliases=["whichanime"],
        enabled=(config.TRACE_MOE_TOKEN is not None),
    )
    @utils.typing_indicator()
    async def find_anime(self, ctx):
        """
        Get an anime from a scene picture, using trace.moe
        """
        img_bytes = None
        msg = None
        tdelta = datetime.datetime.utcnow() - datetime.timedelta(minutes=2)
        async for message in ctx.history(limit=20, after=tdelta, oldest_first=False):
            msg = message
            for atch in message.attachments:
                if not atch.height:  # Not image-type
                    continue
                img_bytes = await atch.read()
                break
            if img_bytes is not None:
                break
            for embed in message.embeds:
                if not embed.image or embed.image is discord.Embed.Empty:
                    continue
                async with self.session.get(embed.image.proxy_url) as sess:
                    img_bytes = await sess.read()
                break
            if img_bytes is not None:
                break

        if img_bytes is None:
            return await ctx.send(
                f"""
No image found in the last 2 minutes (scanned 20 images)!

This command allows you to detect which anime an image is from using <https://trace.moe>
Send an image, then use `{ctx.prefix}{ctx.invoked_with}` to try and detect the anime!
It scans both files and embeds, but it must be a PNG/JPEG/GIF.

**NOTE:** Only *exact* screenshots or images of anime scenes will work.
Read <https://trace.moe/faq> for more info.
            """
            )

        img_io = BytesIO()
        img_io.write(img_bytes)
        img_io.seek(0)
        img = Image.open(img_io, "r")
        img.thumbnail((320, 240), Image.ANTIALIAS)
        img = img.convert("RGB")
        out_io = BytesIO()
        img.save(out_io, "JPEG")
        out_io.seek(0)
        b64_data = b64encode(out_io.getvalue()).decode()
        data = f"data:image/jpeg;base64,{b64_data}"

        async with aiohttp.ClientSession() as sess:
            async with sess.post(
                f"https://trace.moe/api/search?token={config.TRACE_MOE_TOKEN}",
                json={"image": data},
            ) as resp:
                if resp.status == 429:
                    await ctx.send(
                        "Too many people using this command <:Eww:575373991640956938> "
                        "Please wait till quota is cleared."
                    )
                    return
                assert resp.status == 200
                txt = await resp.text()
                try:
                    result = json.loads(txt)["docs"]
                except (json.decoder.JSONDecodeError, KeyError, AssertionError):
                    await ctx.send(
                        "Something is wrong <:Eww:575373991640956938> . Contact developer."
                    )
                    return

        if len(result) == 0:
            await ctx.send("No results found!")
            return
        result = result[0]

        _st = int(result["from"])
        st_min = _st // 60
        st_sec = int(_st - st_min * 60)
        _et = int(result["to"])
        et_min = _et // 60
        et_sec = int(_et - et_min * 60)

        fields = [
            ("Match Similarity", f"{float(result['similarity'])*100:.2f}%", True),
            ("Episode", result["episode"], True),
            (
                "Scene Appears Between",
                f"{st_min:>02d}:{st_sec:>02d} to {et_min:>02d}:{et_sec:>02d}",
                True,
            ),
            ("Is Hentai", str(result["is_adult"]).capitalize(), True),
            (
                "From Message",
                f"[Jump to message (by {msg.author})]({msg.jump_url})",
                True,
            ),
        ]

        anime = await self.jikan.anime(result["mal_id"]) if result["mal_id"] else None
        if anime:
            embed = make_anime_embed(
                anime,
                color=ctx.author.color,
                init_fields=fields,
            )
        else:
            embed = discord.Embed(title=result["title_romaji"], color=ctx.color)
            for field in fields:
                embed.add_field(name=field[0], value=field[1], inline=field[2])

        await ctx.send(embed=embed)


def make_anime_embed(anime, color=0x0, init_fields=None):
    init_fields = init_fields or []
    synopsis = anime["synopsis"]
    if len(synopsis) > 1500:
        synopsis = synopsis[:1500] + "..."
    embed = discord.Embed(
        title=anime["title"], description=synopsis, url=anime["url"], color=color
    )
    if "image_url" in anime.keys() and anime["image_url"]:
        embed.set_image(url=anime["image_url"])
    if len(init_fields) > 0:
        for field in init_fields:
            embed.add_field(name=field[0], value=field[1], inline=field[2])
        embed.add_field(name="**__Anime Info__**", inline=False, value="\u200b")
    embed.add_field(name="Type", value=anime["type"])
    embed.add_field(name="Episodes", value=f"{anime['episodes']} ({anime['duration']})")
    embed.add_field(name="Status", value=anime["status"])
    embed.add_field(name="Aired", value=anime["aired"]["string"])
    embed.add_field(name="Rank", value=anime["rank"])
    if anime["broadcast"]:
        embed.add_field(name="Broadcast", value=anime["broadcast"])
    if anime["premiered"]:
        embed.add_field(name="Premiered", value=anime["premiered"])
    embed.add_field(name="Score", value=f"{anime['score']} by {anime['scored_by']} members")
    embed.add_field(name="Rating", value=anime["rating"], inline=True)
    genres = ", ".join([g["name"] for g in anime["genres"]])
    embed.add_field(name="Genres", value=genres, inline=True)
    if "Adaptation" in anime["related"].keys():
        adaptations = ", ".join(
            [f"{i['name']} ({i['type']})" for i in anime["related"]["Adaptation"]]
        )
        embed.add_field(name="Adaptations", value=adaptations, inline=True)
    if "Prequel" in anime["related"].keys():
        prequels = ", ".join([f"{i['name']} ({i['type']})" for i in anime["related"]["Prequel"]])
        embed.add_field(name="Prequels", value=prequels, inline=True)
    if "Sequel" in anime["related"].keys():
        sequels = ", ".join([f"{i['name']} ({i['type']})" for i in anime["related"]["Sequel"]])
        embed.add_field(name="Sequels", value=sequels, inline=True)
    if len(anime["opening_themes"]) > 0:
        embed.add_field(
            name="Opening Theme Song",
            value="\n".join([f"{i+1}. {j}" for i, j in enumerate(anime["opening_themes"])]),
            inline=False,
        )
    if len(anime["ending_themes"]) > 0:
        embed.add_field(
            name="Ending Theme Song",
            value="\n".join([f"{i+1}. {j}" for i, j in enumerate(anime["ending_themes"])]),
            inline=False,
        )
    embed.set_footer(text="Taken from MyAnimeList.net")
    return embed
