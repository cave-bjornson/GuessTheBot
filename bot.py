import os
from dataclasses import dataclass
from textwrap import dedent

import crescent
import dotenv
import hikari
import rootpath
from hikari import (
    Intents,
    GuildMessageCreateEvent,
    Message,
    MessageCreateEvent,
    DMMessageCreateEvent,
    MessageFlag,
)
from loguru import logger

from src import repository, service
from src.message_processing import process_message

rootpath.append()
dotenv.load_dotenv()


@dataclass
class Model:
    response_hidden: bool = True


bot = hikari.GatewayBot(
    token=os.environ["TOKEN"],
    intents=Intents.ALL_MESSAGES | Intents.MESSAGE_CONTENT | Intents.GUILDS,
)

client = crescent.Client(bot, Model())

model = Model()


async def check_player_exists_hook(ctx: crescent.Context) -> crescent.HookResult:
    not_exists = not repository.player_exists(ctx.user.id)
    if not_exists:
        logger.info("Player not registered, terminating further interaction")
        await ctx.respond(
            ephemeral=True,
            content=f"Du är inte registrerad som spelare, posta ett resultat i <#{os.getenv('GTG_CHANNEL_ID')}> för "
            f"att registrera dig",
            ensure_message=True,
        )
    return crescent.HookResult(exit=not_exists)


async def set_response_visibility_hook(ctx: crescent.Context) -> None:
    is_hidden = not service.is_player_visible(ctx.user.id)
    if is_hidden:
        logger.info(
            "Player with user id {} is invisible, response will be hidden",
            ctx.user.id,
        )

    model.response_hidden = is_hidden


gtb_group = crescent.Group("gtb")


@client.include
@gtb_group.child
@crescent.hook(check_player_exists_hook)
@crescent.command(name="synlighet", description="Var synlig/osynlig på topplistor.")
async def toggle_visibility(ctx: crescent.Context) -> None:
    is_visible = service.toggle_player_visible(ctx.user.id)

    if is_visible:
        msg = "Du är nu synlig på topplistor."
    else:
        msg = "Du är nu gömd och syns inte på topplistor. Du kan fortfarande registrera resultat som vanligt (om du har valt att delta)."

    await ctx.respond(msg, ensure_message=True, ephemeral=True)


@client.include
@gtb_group.child
@crescent.hook(check_player_exists_hook)
@crescent.command(name="deltagande", description="Dina resultat sparas/sparas ej.")
async def toggle_active(ctx: crescent.Context) -> None:
    is_active = service.toggle_player_active(ctx.user.id)

    if is_active:
        msg = "Du har nu registrerat dig. Dina resultat sparas."
    else:
        msg = "Du har nu avregistrerat dig. Dina resultat sparas ej."

    await ctx.respond(msg, ensure_message=True, ephemeral=True)


@client.include
@gtb_group.child
@crescent.hook(check_player_exists_hook)
@crescent.hook(set_response_visibility_hook)
@crescent.command(name="stats", description="Visar dina stats.")
async def stats(ctx: crescent.Context) -> None:
    user_id = 0
    name = ""
    # Check if message is in DM. If None this is a DM.
    if ctx.channel is None:
        user_id = ctx.user.id
        name = "dig"
    else:
        user_id = ctx.member.id
        name = ctx.member.display_name

    pt = repository.get_player_total(user_id, "gtg")
    if pt:
        msg = f"""\
            ### Stats för *{name}*:
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
        msg = ctx.respond(
            "Hittar inga stats för dig, sry!.", ephemeral=True, ensure_message=True
        )

    await ctx.respond(
        ephemeral=model.response_hidden, content=dedent(msg), ensure_message=True
    )


@client.include
@gtb_group.child
@crescent.hook(check_player_exists_hook)
@crescent.command(name="saknade", description="Saknade resultat.")
async def missing(ctx: crescent.Context) -> None:
    dm_channel = await ctx.user.fetch_dm_channel()

    msg = ""
    for gap in repository.get_gaps_in_results(ctx.user.id):
        msg += (f"{gap[0]} - {gap[1]}" if type(gap) is tuple else gap) + os.linesep

    await dm_channel.send(msg)

    await ctx.respond(
        "Saknade resultat skickade i dm", ephemeral=True, ensure_message=True
    )


@client.include
@gtb_group.child
@crescent.command(name="vemärkungen", description="Visar streak-topplistan.")
async def top_streak(ctx: crescent.Context) -> None:
    streak_chart = service.generate_streak_chart()
    msg = ""
    for index, sc in enumerate(streak_chart):
        member = await client.app.rest.fetch_member(
            guild=int(os.getenv("SERVER_ID")), user=sc.user_id
        )
        msg = (
            msg
            + f"{index}. *Streak: {sc.current_streak}* | **{member.display_name}**"
            + os.linesep
        )

    await ctx.respond(content=msg, ensure_message=True)


@client.include()
@crescent.event
async def on_message_create(event: GuildMessageCreateEvent) -> None:
    if event.channel_id != int(os.environ["GTG_CHANNEL_ID"]):
        return

    await guess_message_event_handler(event)


@client.include()
@crescent.event
async def on_message_create(event: DMMessageCreateEvent):
    await guess_message_event_handler(event)


async def guess_message_event_handler(
    event: GuildMessageCreateEvent | DMMessageCreateEvent,
):
    if not event.is_human:
        return

    event_type = type(event)

    channel_name = (
        "GTG-Channel"
        if int(event.channel_id) == int(os.getenv("GTG_CHANNEL_ID"))
        else event.channel_id
    )

    logger.debug(
        "Author {} posted message with id {} {}",
        event.author_id,
        event.message.id,
        f"on channel {channel_name}"
        if event_type is GuildMessageCreateEvent
        else "as as a DM",
    )

    msg = event.message

    if msg.content is None:
        return

    if repository.player_exists(msg.author.id) and not service.is_player_active(
        msg.author.id
    ):
        logger.debug(
            "Player with user id {} has opted out of result saving.", msg.author.id
        )
        return

    res = process_message(
        message_content=msg.content,
        message_id=int(msg.id),
        author_id=int(msg.author.id),
    )

    if res and event_type is DMMessageCreateEvent:
        for r in res:
            await msg.respond(content=r.message)


if __name__ == "__main__":
    bot.run()
