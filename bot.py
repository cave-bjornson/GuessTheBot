from hikari import Intents, GuildMessageCreateEvent
from loguru import logger
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


@bot.listen()
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
