import hashlib
import json
import os
import asyncio
from datetime import datetime
from pathlib import Path

import aiosqlite
import ezcord
from cryptography.fernet import Fernet

from dotenv import load_dotenv

from ezcord import log

from models import Player, PlayerDisplay

load_dotenv()

fernet = Fernet(os.getenv("KEY").encode())


class GuesserDB(ezcord.DBHandler):
    def __init__(self):
        super().__init__(
            path=str(Path(os.getenv("DB_URL"))),
            foreign_keys=True,
            conv_json=True,
        )

    async def setup(self):
        async with aiosqlite.connect(self.DB) as db:
            await db.executescript(open(Path("db/guesser_db.sql")).read())

    async def get_player(self, discord_id: int) -> Player:
        id_hash = self.hash_id(discord_id)
        async with self.start() as db:
            res = await self.one("SELECT * FROM Player WHERE id_hash = ?", id_hash)
            res.row_factory = player_factory
            player = await res.fetchone()

        return player

    async def get_all_players(self) -> list[Player]:
        async with self.start() as db:
            res = await db.exec("SELECT * FROM Player")
            res.row_factory = player_factory
            players = await res.fetchall()

        return list(players)

    async def insert_player(self, discord_id: int):
        id_hash = self.hash_id(discord_id)
        id_enc = fernet.encrypt(str(discord_id).encode())
        async with self.start() as db:
            await db.exec(
                "INSERT OR IGNORE INTO Player (id_hash, id_enc) VALUES (?, ?)",
                (id_hash, id_enc),
            )

    @classmethod
    def hash_id(cls, discord_id: int) -> str:
        return hashlib.sha256(str(discord_id).encode()).hexdigest()


def player_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return Player(**{k: v for k, v in zip(fields, row)})


async def main():
    pass


if __name__ == "__main__":
    asyncio.run(main())
