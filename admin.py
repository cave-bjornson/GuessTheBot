import asyncio
import functools
import os
from contextlib import asynccontextmanager
from datetime import datetime
from loguru import logger
import click
import hikari
import pytz
from dotenv import load_dotenv
from hikari.impl import RESTClientImpl
from pydantic import BaseModel

from src import repository, service
from src.message_processing import process_message
from src.repository import snowflake_to_datetime

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
@make_sync
@click.argument("user_id", required=False)
@click.option("-n", "--name", help="Fetch and display discord username", is_flag=True)
async def players(user_id, name):
    """Outputs one player if DISCORD_ID provided, else all players"""
    if user_id:
        click.echo("Player:")
        p = repository.get_player(user_id=int(user_id))
        await print_model(model=p, user_id=user_id, name=name)
    else:
        click.echo("Players:")
        for p in repository.get_all_players():
            await print_model(model=p, user_id=p.user_id, name=name)


@cli.command()
@make_sync
@click.argument("user_id")
@click.argument("message_id")
async def add_player(user_id, message_id):
    repository.add_player(user_id=user_id, message_id=message_id)


@cli.command("toggle-participation")
@make_sync
@click.argument("user_id", type=int, required=True)
@click.argument(
    "participation-type", type=click.Choice(["visible", "active"]), required=True
)
@click.option("-n", "--name", help="Fetch and display discord username", is_flag=True)
async def toggle_participation(user_id, participation_type, name):
    toggle = (
        service.toggle_player_visible
        if participation_type == "visible"
        else service.toggle_player_active
    )
    updated_participation_val = toggle(user_id=user_id)

    user_display_val = await get_discord_member_name(user_id) if name else user_id
    print(
        f"User {user_display_val} has attribute {participation_type} set to {updated_participation_val}"
    )


@cli.command()
@make_sync
@click.argument("user_id", type=int, required=False)
@click.option("-l", "--limit", type=int)
async def results(user_id: int, limit: int):
    click.echo("Results:")
    for r in repository.get_all_results(user_id=user_id, limit=limit):
        click.echo(r)


@cli.command(name="stats")
@make_sync
@click.argument("user_id", required=True)
@click.option("-n", "--name", help="Fetch and display discord username", is_flag=True)
async def player_stats(user_id, name):
    click.echo("Player Stats:")
    stats = repository.get_player_total(user_id)
    await print_model(model=stats, user_id=user_id, name=name)


@cli.command(name="message")
@make_sync
@click.argument("message", required=True)
@click.option(
    "-c",
    "--channel",
    type=int,
    envvar="GTG_CHANNEL_ID",
    show_default=True,
)
@click.option("-p", "--process", is_flag=True)
async def fetch_message(channel: int, message: int, process):
    click.echo("Message:")
    async with get_client() as client:
        msg = await client.fetch_message(channel=channel, message=message)

    click.echo(
        f"msg-id: {msg.id} msg-timestamp: {msg.timestamp.astimezone()} msg-author-id: {msg.author.id}"
    )
    click.echo(msg.content)

    if process:
        res = process_message(
            message_content=msg.content,
            message_id=int(msg.id),
            author_id=int(msg.author.id),
        )

        if res:
            match = True

            click.echo(
                f"{int(match)}, matches found, {int(res.player_added)} players added,"
                f"{int(res.game_added)} games added, {int(res.result_added)} results added."
            )
        else:
            click.echo("No matches found")


@cli.command("channel-history")
@make_sync
@click.option(
    "-ft",
    "--from-type",
    type=click.Choice(["snowflake", "datetime"]),
    required=True,
    default="snowflake",
)
@click.argument("from-val", type=str)
@click.option(
    "-tt",
    "--to-type",
    type=click.Choice(["snowflake", "datetime"]),
    required=True,
    default="snowflake",
)
@click.argument("to-val", type=str, required=False)
@click.option(
    "-c",
    "--channel",
    type=int,
    envvar="GTG_CHANNEL_ID",
    show_default=True,
)
async def collect_channel_history(from_type, from_val, to_type, to_val, channel):
    """Collects channel history from message snowflake or datetime values."""

    def parse_val(point_type, val: str) -> int | datetime:
        click_datetime_converter = click.DateTime()
        if point_type == "datetime":
            return click_datetime_converter(val).astimezone()
        else:
            return int(val)

    def point_to_datetime(point_type, val) -> datetime:
        if point_type == "datetime":
            return val
        else:
            return snowflake_to_datetime(val)

    from_point = parse_val(from_type, from_val)

    to_datetime = None
    # will stop after time even if last message id not found
    if to_val:
        to_datetime = point_to_datetime(to_type, parse_val(to_type, to_val))

    first_msg_timestamp = None
    last_msg_timestamp = None

    message_count = 0
    match_count = 0
    player_add_count = 0
    game_add_count = 0
    result_add_count = 0

    async with get_client() as client:
        c = await client.fetch_channel(channel)
        # prevents attempts to read messages earlier than channel creation date
        if from_type == "datetime" and from_point < c.created_at:
            from_point = c.created_at

        click.echo(
            f"Collecting results in channel {channel} between {point_to_datetime(point_type=from_type, val=from_point).astimezone()}"
            f" and {to_datetime.astimezone() if to_datetime else 'end of channel history.'}"
        )
        for msg in await c.fetch_history(
            after=from_point,
        ):
            logger.debug(to_datetime)
            logger.debug(msg.timestamp.astimezone())

            if to_datetime and msg.timestamp > to_datetime.astimezone():
                break

            if msg.author.is_bot or msg.author.is_system or msg.content is None:
                continue

            if not first_msg_timestamp:
                first_msg_timestamp = msg.timestamp

            last_msg_timestamp = msg.timestamp

            message_count += 1
            res = process_message(
                message_content=msg.content,
                message_id=int(msg.id),
                author_id=int(msg.author.id),
            )
            if res:
                match_count += 1
                player_add_count += res.player_added
                game_add_count += res.game_added
                result_add_count += res.result_added

    if first_msg_timestamp:
        click.echo(
            f"{message_count} messages read, {match_count}, matches found, {player_add_count} players added,"
            f"{game_add_count} games added, {result_add_count} results added."
        )
        click.echo(
            f"First message timestamp: {first_msg_timestamp.astimezone()}, Last message timestamp: {last_msg_timestamp.astimezone()}"
        )
    else:
        click.echo("No messages read")


async def get_discord_name(user_id: int):
    async with get_client() as client:
        u = await client.fetch_user(user_id)

    return u.global_name


async def get_discord_member_name(
    user_id: int, server_id: int = int(os.getenv("SERVER_ID"))
):
    async with get_client() as client:
        m = await client.fetch_member(guild=server_id, user=user_id)

    return m.display_name


async def print_model(model: BaseModel, user_id: int, name: bool = False):
    user_name = None
    if name:
        user_name = await get_discord_member_name(user_id)

    click.echo(f"Name={user_name or 'excluded'} {model.model_dump_json()}")


if __name__ == "__main__":
    cli()
