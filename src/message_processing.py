import re
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from typing import NamedTuple

from loguru import logger

from src import repository
from src.models import check_guesses
from src.repository import game_exists

gtg_pattern = re.compile(
    r"(?P<tag>[#🔍].*GuessTheGame)?[.\s]*#(?P<id>\d+)?[.\s]*(🎮\s*(?P<score>(\s*[🟥🟩🟨](\s*[🟥🟩🟨⬜⬛]){5})))",
    flags=(re.DOTALL and re.IGNORECASE),
)

gtg_first_date = date(year=2022, month=5, day=15)


class PatternResult(NamedTuple):
    game_identifier: str
    guesses: int


@dataclass
class ProcessResult:
    player_added: bool = False
    game_added: bool = False
    result_added: bool = False


def get_gtg_result(msg_content: str, submit_date: date) -> PatternResult | None:
    res = re.search(gtg_pattern, msg_content)
    # if no score group return early
    if res is None:
        return None

    # if no id compute id from submit date
    if res.group("id") is None:
        td = submit_date - gtg_first_date
        id_string = str(td.days + 1)
    else:
        id_string = res.group("id")

    score_str = re.sub(r"\s", "", res.group("score"))
    err_val = score_str.find("🟩")
    guesses = err_val + 1 if err_val >= 0 else 6

    check_guesses(guesses)

    logger.debug(
        f"Pattern for GuessThe.Game found with identifier {id_string} with {guesses} guesses"
    )
    return PatternResult(game_identifier=id_string, guesses=guesses)


def process_game(
    message_content: str, submit_time: datetime, author_id: int
) -> ProcessResult | None:
    result = get_gtg_result(message_content, submit_time.date())
    if not result:
        return

    process_result = ProcessResult()

    if not repository.player_exists(author_id):
        repository.add_player(author_id)
        process_result.player_added = True

    post_date = gtg_first_date + timedelta(days=(int(result.game_identifier) - 1))

    if not game_exists(result.game_identifier):
        repository.add_game("GuessThe.Game", result.game_identifier, post_date)
        process_result.game_added = True

    if repository.result_exists(
        discord_id=author_id, game_identifier=result.game_identifier
    ):
        return process_result

    repository.add_result(
        discord_id=author_id,
        game_identifier=result.game_identifier,
        submit_time=submit_time,
        guesses=result.guesses,
    )

    process_result.result_added = True

    return process_result
