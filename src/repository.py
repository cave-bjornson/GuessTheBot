import asyncio
import hashlib
import os
from datetime import date, datetime

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from loguru import logger
from pony.orm import db_session, select, Database, exists

from src.models import Player, PlayerDto, Game, GameType, Result, ResultDto, PlayerTotal

load_dotenv()

fernet = Fernet(os.getenv("KEY").encode())

db = Database()


def hash_discord_id(discord_id: int) -> str:
    return hashlib.sha256(str(discord_id).encode()).hexdigest()


@db_session
def player_exists(discord_id: int) -> bool:
    d_id_hash = hash_discord_id(discord_id)
    return Player.exists(discord_id_hash=d_id_hash)


def get_player(discord_id: int) -> PlayerDto | None:
    with db_session:
        d_id_hash = hash_discord_id(discord_id)
        p: Player = Player.get(discord_id_hash=d_id_hash)
        if p:
            player = player_to_dto(p)
        else:
            player = None

    return player


@db_session
def get_all_players() -> list[PlayerDto]:
    query = Player.select()
    players = list(map(player_to_dto, query))

    return players


def add_player(discord_id: int, join_date: date = date.today()):
    with db_session:
        d_id_hash = hash_discord_id(discord_id)
        if not Player.exists(discord_id_hash=d_id_hash):
            d_id_enc = fernet.encrypt(str(discord_id).encode())
            p = Player(
                join_date=join_date,
                discord_id_hash=d_id_hash,
                discord_id_encrypted=d_id_enc,
            )
            p.flush()
            logger.debug("Player added with primary key {}.", p.id)
        else:
            logger.warning("Attempt to add existing player")


@db_session
def game_exists(identifier: str) -> bool:
    return Game.exists(identifier=identifier)


def add_game(game_type_name: str, identifier: str, post_date: date):
    with db_session:
        gt = GameType.get(name=game_type_name)
        g = Game(game_type=gt, identifier=identifier, post_date=post_date)
        g.flush()
        logger.info(
            "Game of {} with identifier {} added with primary key {}.",
            gt.name,
            g.identifier,
            g.id,
        )


@db_session
def result_exists(discord_id: int, game_identifier: str):
    d_id_hash = hash_discord_id(discord_id)
    return exists(
        r
        for r in Result
        if r.player.discord_id_hash == d_id_hash
        and r.game.identifier == game_identifier
    )


def add_result(
    discord_id: int, game_identifier: str, submit_time: datetime, guesses: int
):
    d_id_hash = hash_discord_id(discord_id)
    with db_session:
        p = Player.get(discord_id_hash=d_id_hash)
        g = Game.get(identifier=game_identifier)
        gametype_name = g.game_type.name
        r = Result(player=p, game=g, submit_time=submit_time, guesses=guesses)
        r.flush()
        logger.info(
            "Result of {} guesses for {} with identifier {} with submit-time {} added with primary key {}.",
            guesses,
            gametype_name,
            g.identifier,
            submit_time,
            r.id,
        )


@db_session
def get_all_results():
    query = Result.select().order_by(Result.submit_time)
    results = list(map(result_to_dto, query))

    return results


def get_player_total(discord_id: int, game_type_name: str = "GuessThe.Game"):
    d_id_hash = hash_discord_id(discord_id)
    with db_session:
        player_encrypted_id = select(
            p.discord_id_encrypted for p in Player if p.discord_id_hash == d_id_hash
        )[:]

        results = Result.select(
            lambda r: r.player.discord_id_hash == d_id_hash
            and r.game.game_type.name == game_type_name
        ).order_by(Result.submit_time)

        decrypted_id = int(fernet.decrypt(player_encrypted_id[0]))
        played_games = 0
        won = 0
        current_streak = 0
        max_streak = 0
        loosing_streak = 0
        max_loosing_streak = 0

        for res in results:
            played_games += 1
            if res.guesses < 6:
                loosing_streak = 0
                won += 1
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0
                loosing_streak += 1
                if loosing_streak > max_loosing_streak:
                    max_loosing_streak = loosing_streak

        win_rate = f"{won / played_games:.2%}"

        total = PlayerTotal(
            discord_id=decrypted_id,
            played_games=played_games,
            won=won,
            win_rate=win_rate,
            current_streak=current_streak,
            max_streak=max_streak,
            max_loosing_streak=max_loosing_streak,
        )

    return total


def player_to_dto(player: Player) -> PlayerDto:
    p = PlayerDto.model_validate(player)
    p.discord_id = int(fernet.decrypt(player.discord_id_encrypted))
    return p


def result_to_dto(result: Result) -> ResultDto:
    r = ResultDto.model_validate(result)
    r.player_discord_id = int(fernet.decrypt(result.player.discord_id_encrypted))
    r.game_type_name = result.game.game_type.name
    r.game_identifier = result.game.identifier
    return r


async def main():
    pass


if __name__ == "__main__":
    asyncio.run(main())
