from discord.ext import commands


class NoneBalance(Exception):
    pass


class NotEnoughBalance(Exception):
    pass


class LockedCommand(commands.CheckFailure):
    pass


class BotNotReady(commands.CheckFailure):
    pass
