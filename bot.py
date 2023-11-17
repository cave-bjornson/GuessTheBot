from textwrap import dedent
from typing import Annotated

import crescent
from hikari import Intents, GuildMessageCreateEvent
from loguru import logger

from src import repository
from src.message_processing import process_message
import dotenv
import hikari
import os
import rootpath

rootpath.append()
dotenv.load_dotenv()

bot = hikari.GatewayBot(
    token=os.environ["TOKEN"], intents=Intents.ALL_MESSAGES | Intents.MESSAGE_CONTENT
)
client = crescent.Client(bot)


@client.include
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
        msg = "Hittar inga stats för dig, sry!."

    await ctx.respond(dedent(msg))


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
