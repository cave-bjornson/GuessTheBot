import asyncio
import datetime
import functools
import os
from contextlib import asynccontextmanager

import click
import hikari
import pytz
from dotenv import load_dotenv
from hikari.impl import RESTClientImpl

from src import repository
from src.message_processing import process_game

load_dotenv()
token = os.getenv("TOKEN")

utc = pytz.timezone("UTC")


@asynccontextmanager
async def get_client() -> RESTClientImpl:
    rest_app = hikari.RESTApp()
    await rest_app.start()
    async with rest_app.acquire(token_type="Bot", token=os.environ["TOKEN"]) as client:
        try:
            yield client
        finally:
            await rest_app.close()


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
@click.argument("discord_id")
@click.option("-n", "--name", is_flag=True)
@make_sync
async def get_player(discord_id, name):
    p = repository.get_player(discord_id=int(discord_id))
    u = None
    if name:
        async with get_client() as client:
            u = await client.fetch_user(p.discord_id)

    print(f"{p} Name={u.global_name if u else 'excluded'}")


@cli.command()
@click.option("-n", "--name", is_flag=True)
@make_sync
async def players(name):
    """List all players"""
    print("Players:")
    async with get_client() as client:
        for p in repository.get_all_players():
            u = None
            if name:
                u = await client.fetch_user(p.discord_id)

            print(f"{p} Name={u.global_name if u else 'excluded'}")


@cli.command()
@click.argument("discord_id")
@make_sync
async def add_player(discord_id):
    repository.add_player(discord_id=discord_id)


@cli.command()
@make_sync
async def results():
    print("Results:")
    for r in repository.get_all_results():
        print(r)


@cli.command()
@click.argument("discord_id")
@make_sync
async def player_total(discord_id):
    print("Player Total:")
    print(repository.get_player_total(discord_id))


@cli.command()
@make_sync
@click.option("-f", "--from-date", default=datetime.date.today(), show_default=True)
@click.option("-t", "--to-date", default=datetime.date.today(), show_default=True)
@click.option(
    "-c",
    "--channel",
    type=int,
    default=int(os.environ["GTG_CHANNEL_ID"]),
    show_default=True,
)
async def collect_channel_history(from_date, to_date, channel):
    """Collects channel history. defaults to today. Dates are inclusive."""
    fd = datetime.datetime.combine(
        datetime.date.fromisoformat(from_date),
        datetime.time.min,
    )
    td = datetime.datetime.combine(
        datetime.date.fromisoformat(to_date),
        datetime.time.max,
    )
    fd = fd.astimezone(utc)
    td = td.astimezone(utc)
    first_msg_timestamp = None
    last_msg_timestamp = None
    message_count = 0
    match_count = 0
    player_add_count = 0
    game_add_count = 0
    result_add_count = 0

    async with get_client() as client:
        c = await client.fetch_channel(channel)
        fd = c.created_at if fd < c.created_at else fd
        print(f"Collecting results between {fd} and {td}")
        for msg in await c.fetch_history(
            after=fd,
        ):
            if msg.author.is_bot or msg.author.is_system or msg.content is None:
                continue

            time_stamp = msg.timestamp.astimezone()
            if not first_msg_timestamp:
                first_msg_timestamp = time_stamp

            last_msg_timestamp = time_stamp

            if msg.timestamp > td:
                break

            message_count += 1
            res = process_game(
                message_content=msg.content,
                submit_time=time_stamp,
                author_id=msg.author.id,
            )
            if res:
                match_count += 1
                player_add_count += res.player_added
                game_add_count += res.game_added
                result_add_count += res.result_added

    print(
        f"{message_count} messages read, {match_count}, matches found, {player_add_count} players added,"
        f"{game_add_count} games added, {result_add_count} results added."
    )
    print(
        f"First message timestamp: {first_msg_timestamp}, Last message timestamp: {last_msg_timestamp}"
    )


if __name__ == "__main__":
    cli()
