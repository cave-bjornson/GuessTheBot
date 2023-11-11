import asyncio
import functools
import os
from contextlib import asynccontextmanager

import click
import discord
from discord import User
from dotenv import load_dotenv

from models import PlayerDisplay
from repository import GuesserDB, fernet

load_dotenv()
token = os.getenv("TOKEN")


@asynccontextmanager
async def get_client():
    intents = discord.Intents(message_content=True, messages=True, members=True)
    client = discord.Client(intents=intents)
    await client.login(token)
    try:
        yield client
    finally:
        await client.close()


def make_sync(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.group()
@make_sync
async def cli():
    pass


@cli.command()
@make_sync
async def players():
    """List all players"""
    gdb = GuesserDB()
    print("Players")
    async with get_client() as client:
        for p in await gdb.get_all_players():
            d_id = int(fernet.decrypt(p.id_enc))
            user: User = await client.get_or_fetch_user(d_id)
            pd = PlayerDisplay(name=user.display_name, join_date=p.join_date.date())
            print(pd)


@cli.command()
@make_sync
async def db():
    """Initialize Db Schema"""
    gdb = GuesserDB()
    await gdb.setup()


if __name__ == "__main__":
    cli()
