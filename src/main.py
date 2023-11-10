import discord
import ezcord
from discord import Message, User, Member

# from dpyConsole import Console
from ezcord import log

from models import PlayerDisplay
from repository import GuesserDB, fernet

db = GuesserDB()

intents = discord.Intents(message_content=True, messages=True, members=True)

bot = ezcord.Bot(intents=intents)


@bot.listen()
async def on_message(message: Message):
    log.info(message.content)


@my_console.command()
async def echo(text):
    log.info(text)


@my_console.command()
async def players():
    for p in await db.get_all_players():
        d_id = int(fernet.decrypt(p.id_enc))
        user: User = await bot.get_or_fetch_user(d_id)
        pd = PlayerDisplay(name=user.display_name, join_date=p.join_date.date())
        print(pd)


if __name__ == "__main__":
    bot.run()
