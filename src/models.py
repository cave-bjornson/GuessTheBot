import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pony.orm
import rootpath
from dotenv import load_dotenv
from pony.orm import Database, PrimaryKey, Required, Set
from pydantic import BaseModel, ConfigDict, AfterValidator
from typing_extensions import Annotated

load_dotenv()

path = rootpath.detect()

db = Database(
    provider="sqlite",
    filename=str(Path(path) / "data" / os.getenv("DB_FILE")),
    create_db=True,
)


def check_guesses(v: int) -> int:
    assert 1 <= v <= 6, f"guesses {v} should be between 1 and 6"
    return v


class PlayerDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    discord_id: Optional[int] = None
    join_date: date
    active: bool
    visible: bool


class Player(db.Entity):
    id = PrimaryKey(int, auto=True)
    join_date = Required(date)
    discord_id_hash = Required(str, unique=True)
    discord_id_encrypted = Required(bytes)
    active = Required(bool, default=True)
    visible = Required(bool, default=True)
    results = Set("Result")


class GameType(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str, unique=True)
    publish_date = Required(date)
    games = Set("Game")


class Game(db.Entity):
    id = PrimaryKey(int, auto=True)
    game_type = Required(GameType)
    identifier = Required(str, unique=True)
    title = pony.orm.Optional(str)
    post_date = Required(date)
    results = Set("Result")


class Result(db.Entity):
    id = PrimaryKey(int, auto=True)
    player = Required(Player)
    game = Required(Game)
    submit_time = Required(datetime)
    guesses = Required(int)


GuessNumber = Annotated[int, AfterValidator(check_guesses)]


class ResultDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guesses: GuessNumber
    player_discord_id: Optional[int] = None
    game_type_name: Optional[str] = None
    game_identifier: Optional[str] = None
    submit_time: datetime
    guesses: int
    game_title: Optional[str] = None


class PlayerTotal(BaseModel):
    discord_id: int
    played_games: int
    won: int
    win_rate: str
    current_streak: int
    max_streak: int
    max_loosing_streak: int


# if os.getenv("ENVIRONMENT") == "dev":
#     set_sql_debug(debug=True)

db.generate_mapping(check_tables=True, create_tables=True)
