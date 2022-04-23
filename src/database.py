import logging

import sqlalchemy as sa
from databases import Database

import errors
from config import DATABASE_URL

logging.basicConfig(level=logging.INFO)


meta = sa.MetaData()

Member = sa.Table(
    "members",
    meta,
    sa.Column("id", sa.BigInteger, primary_key=True, nullable=False),
    sa.Column("member", sa.BigInteger, nullable=False, unique=True),
    sa.Column("wallet", sa.BigInteger, default=0, nullable=False),
    sa.Column("last_dailies", sa.DateTime),
    sa.Column("last_hourlies", sa.DateTime),
    sa.Column("last_reward", sa.DateTime),
    sa.Column("tier", sa.SmallInteger, server_default="0"),
)

Guild = sa.Table(
    "guild",
    meta,
    sa.Column("id", sa.BigInteger, primary_key=True, nullable=False),
    sa.Column("guild", sa.BigInteger, nullable=False, unique=True),
    sa.Column("music_enabled", sa.Boolean),
    sa.Column("coin_drops", sa.Boolean, server_default="f", nullable=False),
    sa.Column("join_leave_channel", sa.BigInteger),
    sa.Column(
        "welcome_str",
        sa.String(length=60),
        server_default="Let the madness begin. Hold tight.",
    ),
    sa.Column(
        "leave_str",
        sa.String(length=60),
        server_default="See you again, in another life.",
    ),
    sa.Column("custom_role", sa.BigInteger, server_default="40000"),
)

Waifu = sa.Table(
    "waifu",
    meta,
    sa.Column("id", sa.BigInteger, primary_key=True, nullable=False),
    sa.Column("name", sa.String(length=200), nullable=False),
    sa.Column("from_anime", sa.String(length=200), nullable=False),
    sa.Column("gender", sa.String(length=1)),
    sa.Column("price", sa.BigInteger, nullable=False),
    sa.Column("description", sa.Text),
    sa.Column("image_url", sa.Text),
)

PurchasedWaifu = sa.Table(
    "purchased_waifu",
    meta,
    sa.Column("id", sa.BigInteger, primary_key=True, nullable=False, unique=True),
    sa.Column("member_id", sa.BigInteger, sa.ForeignKey("members.id", ondelete="CASCADE")),
    sa.Column("waifu_id", sa.BigInteger, sa.ForeignKey("waifu.id", ondelete="CASCADE")),
    sa.Column("guild", sa.BigInteger, nullable=False),
    sa.Column("member", sa.BigInteger, nullable=False),
    sa.Column("purchased_for", sa.BigInteger, nullable=False),
    sa.Column("favorite", sa.Boolean, nullable=False, server_default="f"),
)

tables = [Member, Guild, Waifu, PurchasedWaifu]

indexes = [
    sa.Index(
        "purchased_waifu_key",
        PurchasedWaifu.c.guild,
        PurchasedWaifu.c.member,
        PurchasedWaifu.c.waifu_id,
        unique=True,
    ),
    # PostgreSQL indexes for better search
    sa.Index(
        "idx_trgm_name",
        Waifu.c.name,
        postgresql_ops={"name": "gist_trgm_ops"},
        postgresql_using="gist",
    ),
    sa.Index(
        "idx_trgm_from_anime",
        Waifu.c.from_anime,
        postgresql_ops={"from_anime": "gist_trgm_ops"},
        postgresql_using="gist",
    ),
]

ENGINE = None


async def prepare_engine():
    global ENGINE
    if ENGINE is None:
        ENGINE = Database(DATABASE_URL)
        await ENGINE.connect()
    return ENGINE


def create_index(index, engine):
    conn = engine.connect()
    result = conn.execute(
        f"SELECT exists(SELECT 1 from pg_indexes where indexname = '{index.name}') as ix_exists;",
    ).first()
    if not result.ix_exists:
        index.create(engine)


def prepare_tables():
    # Easier to use sqlalchemy to create tables.
    engine = sa.create_engine(DATABASE_URL)
    for table in tables:
        table.create(engine, checkfirst=True)
    for index in indexes:
        create_index(index, engine)


async def make_member_profile(members_list):
    engine = await prepare_engine()
    create_query_values = []
    creating_ids = []

    for member in members_list:
        if member.id in creating_ids:
            continue
        exists_query = Member.count(None).where(  # pylint: disable=no-member
            Member.c.member == member.id
        )
        res = await engine.fetch_val(query=exists_query)

        if res == 0:
            creating_ids.append(member.id)
            create_query_values.append({"member": member.id, "wallet": 0})
            logging.debug("Creating profile for member %s.", member.name)

    if len(create_query_values) > 0:
        create_query = Member.insert(None)
        await engine.execute_many(query=create_query, values=create_query_values)


async def make_guild_entry(guilds_list):
    engine = await prepare_engine()
    create_query_values = []
    creating_ids = []

    for guild in guilds_list:
        if guild.id in creating_ids:
            continue
        exists_query = Guild.count(None).where(  # pylint: disable=no-member
            Guild.c.guild == guild.id
        )
        res = await engine.fetch_val(query=exists_query)

        if res == 0:
            creating_ids.append(guild.id)
            create_query_values.append(
                {
                    "guild": guild.id,
                }
            )
        logging.debug("Creating entry for guild %s.", guild.name)

    if len(create_query_values) > 0:
        create_query = Guild.insert(None)
        await engine.execute_many(query=create_query, values=create_query_values)


async def fetch_wallet(member):
    engine = await prepare_engine()
    fetch_query = Member.select().where(Member.c.member == member.id)
    resp = await engine.fetch_one(query=fetch_query)
    if resp is None:
        raise errors.NoneBalance

    return resp[Member.c.wallet]


async def add_money(member, amount):
    amount = abs(amount)
    current_balance = await fetch_wallet(member)
    engine = await prepare_engine()
    update_query = (
        Member.update(None)
        .where(Member.c.member == member.id)
        .values(wallet=Member.c.wallet + amount)
    )
    await engine.execute(update_query)
    return current_balance + amount


async def remove_money(member, amount):
    amount = abs(amount)
    current_balance = await fetch_wallet(member)
    if current_balance - amount < 0:
        raise errors.NotEnoughBalance
    engine = await prepare_engine()
    update_query = (
        Member.update(None)
        .where(Member.c.member == member.id)
        .values(wallet=Member.c.wallet - amount)
    )
    await engine.execute(update_query)
    return current_balance - amount
