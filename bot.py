from dataclasses import dataclass
from textwrap import dedent
from typing import Annotated, Callable

import crescent
from crescent import Context
from hikari import Intents, GuildMessageCreateEvent
from loguru import logger

from src import repository, service
from src.message_processing import process_message
import dotenv
import hikari
import os
import rootpath

rootpath.append()
dotenv.load_dotenv()


@dataclass
class Model:
    response_hidden: bool = True


bot = hikari.GatewayBot(
    token=os.environ["TOKEN"], intents=Intents.ALL_MESSAGES | Intents.MESSAGE_CONTENT
)

client = crescent.Client(bot, Model())

model = Model()


async def check_player_exists_hook(ctx: crescent.Context) -> crescent.HookResult:
    not_exists = not repository.player_exists(ctx.user.id)
    if not_exists:
        logger.info("Player not registered, terminating further interaction")
        await ctx.respond(
            ephemeral=True,
            content=f"Du är inte registrerad som spelare, posta ett resultat i <#{os.getenv('GTG_CHANNEL_ID')}> för att registrera dig",
            ensure_message=True,
        )
    return crescent.HookResult(exit=not_exists)


async def set_response_visibility_hook(ctx: crescent.Context) -> None:
    is_hidden = not service.get_player_visibility(ctx.user.id)
    if is_hidden:
        logger.info(
            "Player with user id {} is invisible, response will be hidden",
            ctx.user.id,
        )

    model.response_hidden = is_hidden


@client.include
@crescent.hook(check_player_exists_hook)
@crescent.hook(set_response_visibility_hook)
@crescent.command
async def gtb(ctx: crescent.Context) -> None:
    pt = repository.get_player_total(ctx.member.id, "gtg")
    if pt:
        msg = f"""\
            ### Stats för *{ctx.member.display_name}*:
            🔍 Spel: 🎮 GuessThe.Game
            🤔 Spelade: {pt.played_games}
            🥳 Vunna: {pt.won}
            🧮 Ratio: {pt.win_rate}
            🟨 Nuvarande streak: {pt.current_streak}
            🟩 Bästa streak: {pt.max_streak}
            🟥 Värsta Streak: {pt.max_loosing_streak}
            📅 Första spel: {pt.join_date.strftime("%y-%m-%d")}
            """
    else:
        msg = ctx.respond("Hittar inga stats för dig, sry!.")

    await ctx.respond(
        ephemeral=model.response_hidden, content=dedent(msg), ensure_message=True
    )


@client.include()
@crescent.event
async def on_message_create(event: GuildMessageCreateEvent) -> None:
    if event.channel_id != int(os.environ["GTG_CHANNEL_ID"]):
        return

    logger.debug(f"Message with id {event.message.id} posted on GTG channel")

    if not event.is_human:
        return

    msg = event.message

    if msg.content is None:
        return

    process_message(
        message_content=msg.content,
        message_id=int(msg.id),
        author_id=int(msg.author.id),
    )


if __name__ == "__main__":
    bot.run()
