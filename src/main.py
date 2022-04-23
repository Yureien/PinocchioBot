import asyncio
import logging

import config
import modules


async def main():
    await modules.before_start()
    await modules.bot.start(config.TOKEN)


if __name__ == "__main__":
    if not config.DEV_MODE:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        loop.close()
