# Pinocchio Bot

[![Discord Bots](https://discordbots.org/api/widget/status/506878658607054849.svg)](https://discordbots.org/bot/506878658607054849) [![CI Status](https://git.sohamsen.me/Pinocchio/PinocchioBot/badges/master/pipeline.svg)](https://git.sohamsen.me/Pinocchio/PinocchioBot)

[![Discord Bots](https://discordbots.org/api/widget/506878658607054849.svg)](https://discordbots.org/bot/506878658607054849)

**Support Server:** https://discord.gg/BzaksqP

**Requirements:** Python 3.8, PostgreSQL (optional but recommended. Some features won't work/will bug out without it)

## Installation

All the dependencies are in `requirements.txt`. Install with:
```
pip install -r requirements.txt
```

Linux users can use `./scripts/install`. This will also set up a virtual environment.

## Configuration

To run the bot, you need to have some environmental variables. You can either export them directly with your shell (`export KEY=VALUE`) or create a `.env` file with required configuration. Check `variables.py` for a complete list of env vars.

Sample configuration (`.env`):
```
DATABASE_URL=postgresql://username:password@localhost/database_name
TOKEN=<Bot Token>
PREFIX=.
DEV_MODE=False
```

For PostgreSQL, for some features to work, you need to enable the `pg_trgm` extension. To do it via `psql`:
```
CREATE EXTENSION pg_trgm;
```

Contact me if you are contributing to this bot and require a sample of the production database to populate initial tables (such as `waifus`).

#### Running the bot on Unix-based OS (with scripts)

Just do:
```
./scripts/run
```

#### Running the bot on Windows + Unix-based OS (without scripts)

```
cd src
python main.py
```

## Contribution

Create an issue or pull request as you see fit!

If you are creating a pull request, ensure:
1. To use `black` as your PEP-8 formatter, **NOT** the default `autopep8`. (It's better!)
2. If you're on Linux, it's highly recommended to do `./scripts/lint` to lint your code and `./scripts/test` to test it.
3. If you're on Windows (and for Linux peeps too), well ¯\\\_(ツ)\_/¯. Set up your IDE/editor with `black`, `pylint`, `autoflake` and `isort`.
