import os
from datetime import date, datetime
from functools import total_ordering
from pathlib import Path
from typing import Optional

import pony.orm
import rootpath
from dotenv import load_dotenv
from pony.orm import Database, PrimaryKey, Required, Set, set_sql_debug, db_session
from pydantic import BaseModel

load_dotenv()

path = rootpath.detect()

db = Database(
    provider="sqlite",
    filename=str(Path(path) / "data" / os.getenv("DB_FILE")),
    create_db=True,
)


class PlayerDto(BaseModel):
    user_id: int
    join_date: date
    active: bool
    visible: bool


class Player(db.Entity):
    id = PrimaryKey(int, auto=True)
    user_snowflake = Required(int, unique=True, size=64)
    join_datetime = Required(datetime)
    active = Required(bool, default=True)
    visible = Required(bool, default=True)
    results = Set("Result")


class GameType(db.Entity):
    id = PrimaryKey(int, auto=True)
    identifier = Required(str, unique=True)
    name = Required(str, unique=True)
    publish_date = Required(date)
    games = Set("Game")


class Game(db.Entity):
    id = PrimaryKey(int, auto=True)
    game_type = Required(GameType)
    identifier = Required(str, unique=True)
    title = pony.orm.Optional(str)
    publish_date = Required(date)
    results = Set("Result")


class Result(db.Entity):
    id = PrimaryKey(int, auto=True)
    message_snowflake = Required(int, size=64)
    player = Required(Player)
    game = Required(Game)
    submit_time = Required(datetime)
    guesses = Required(int)


class ResultDto(BaseModel):
    submit_time: datetime
    message_id: int
    user_id: int
    game_type_name: str
    game_identifier: str
    game_title: Optional[str] = None
    guesses: Optional[int] = None
    won: bool


class PlayerTotal(BaseModel):
    user_id: int
    played_games: int
    won: int
    win_rate: str
    current_streak: int
    max_streak: int
    max_loosing_streak: int
    join_date: datetime


@total_ordering
class PlayerStreak(BaseModel):
    user_id: int
    current_streak: int
    total_guesses: int
    last_submit_time: datetime

    def __lt__(self, other):
        return (self.current_streak, -self.total_guesses, self.last_submit_time) > (
            other.current_streak,
            -other.total_guesses,
            other.last_submit_time,
        )


if os.getenv("ENVIRONMENT") == "dev":
    set_sql_debug(debug=True)

db.generate_mapping(check_tables=True, create_tables=True)


@db_session
def populate_database():
    GameType(
        identifier="gtg",
        name="GuessThe.Game",
        publish_date=date(year=2022, month=5, day=15),
    )


if __name__ == "__main__":
    with db_session:
        if GameType.select().first() is None:
            populate_database()
