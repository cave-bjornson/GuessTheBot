import discord
import ezcord
from discord import Message

from ezcord import log

from repository import GuesserDB

db = GuesserDB()

intents = discord.Intents(message_content=True, messages=True, members=True)

bot = ezcord.Bot(intents=intents)


@bot.listen()
async def on_message(message: Message):
    log.info(message.content)


if __name__ == "__main__":
    bot.run()
