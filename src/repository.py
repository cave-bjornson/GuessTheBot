import asyncio
from datetime import date

import snowflake
from dotenv import load_dotenv
from loguru import logger
from pony.orm import db_session, Database, exists, count, select

from src.models import Player, PlayerDto, Game, GameType, Result, ResultDto, PlayerTotal

load_dotenv()

db = Database()


snow = snowflake.Snowflake()


@db_session
def player_exists(user_id: int) -> bool:
    return Player.exists(user_snowflake=user_id)


def get_player(user_id: int) -> PlayerDto | None:
    with db_session:
        p: Player = Player.get(user_snowflake=user_id)
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


def add_player(user_id: int, message_id):
    with db_session:
        if not Player.exists(user_snowflake=user_id):
            p = Player(
                user_snowflake=user_id,
                join_datetime=snowflake_to_datetime(message_id),
            )
            p.flush()
            logger.debug("Player added with primary key {}.", p.id)
        else:
            logger.warning("Attempt to add existing player")


@db_session
def game_exists(identifier: str) -> bool:
    return Game.exists(identifier=identifier)


def add_game(game_type_identifier: str, game_identifier: str, publish_date: date):
    with db_session:
        gt = GameType.get(identifier=game_type_identifier)
        g = Game(game_type=gt, identifier=game_identifier, publish_date=publish_date)
        g.flush()
        logger.info(
            "Game of {} with identifier {} added with primary key {}.",
            gt.name,
            g.identifier,
            g.id,
        )


@db_session
def result_exists(user_id: int, game_identifier: str):
    return exists(
        r
        for r in Result
        if r.player.user_snowflake == user_id and r.game.identifier == game_identifier
    )


def add_result(user_id: int, message_id, game_identifier: str, guesses: int):
    with db_session:
        p = Player.get(user_snowflake=user_id)
        g = Game.get(identifier=game_identifier)
        game_type_name = g.game_type.name
        r = Result(
            player=p,
            game=g,
            submit_time=snowflake_to_datetime(message_id),
            guesses=guesses,
            message_snowflake=message_id,
        )
        r.flush()
        logger.info(
            "Result of {} guesses for {} with identifier {} with submit-time {} added with primary key {}.",
            guesses,
            game_type_name,
            g.identifier,
            r.submit_time.astimezone(),
            r.id,
        )


def get_all_results(limit: int, user_id: int = None):
    sel = (lambda r: r.player.user_snowflake == user_id) if user_id else lambda x: x
    with db_session:
        query = Result.select(sel).order_by(Result.submit_time).limit(limit)
        results = list(map(result_to_dto, query))

    return results


def get_player_total(
    user_id: int, game_type_identifier: str = "gtg"
) -> PlayerTotal | None:
    user_id = int(user_id)
    with db_session:
        results = Result.select(
            lambda r: r.player.user_snowflake == user_id
            and r.game.game_type.identifier == game_type_identifier
        ).order_by(lambda r: r.game.publish_date)

        if not results.first():
            return None

        played_games = 0
        won = 0
        current_streak = 0
        max_streak = 0
        loosing_streak = 0
        max_loosing_streak = 0

        for res in results:
            played_games += 1
            if res.guesses != 0:
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

        join_date_res = select(
            p.join_datetime for p in Player if p.user_snowflake == user_id
        )

        total = PlayerTotal(
            user_id=user_id,
            played_games=played_games,
            won=won,
            win_rate=win_rate,
            current_streak=current_streak,
            max_streak=max_streak,
            max_loosing_streak=max_loosing_streak,
            join_date=join_date_res.first(),
        )

    return total


def player_to_dto(player: Player) -> PlayerDto:
    return PlayerDto(
        user_id=player.user_snowflake,
        join_date=player.join_datetime.astimezone().date(),
        active=player.active,
        visible=player.active,
    )


def result_to_dto(result: Result) -> ResultDto:
    return ResultDto(
        submit_time=result.submit_time.astimezone(),
        message_id=result.message_snowflake,
        user_id=result.player.user_snowflake,
        game_type_name=result.game.game_type.name,
        game_identifier=result.game.identifier,
        won=result.guesses != 0,
        guesses=result.guesses or None,
    )


def snowflake_to_datetime(snowflake_val: int):
    snowflake_datetime, *_ = snow.parse_discord_snowflake(str(snowflake_val))
    return snowflake_datetime


async def main():
    pass


if __name__ == "__main__":
    asyncio.run(main())
