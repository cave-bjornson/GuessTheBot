import os
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import NamedTuple

from loguru import logger

from src import repository
from src.repository import game_exists

gtg_pattern = re.compile(
    r"(?P<tag>[#🔍].*GuessTheGame)?[.\s]*(?P<id_group>#(?P<id>\d+))?[.\s]*(?P<score_group>🎮\s*(?P<score>(\s*[🟥🟩🟨](\s*[🟥🟩🟨⬜⬛\uFE0F]){0,5})))",
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
    message: str = ""


def get_gtg_result(msg_content: str, submit_date: date) -> list[PatternResult] | None:
    res = re.finditer(gtg_pattern, msg_content)
    # if no score group return early
    if not res:
        return None

    pattern_results = list[PatternResult]()

    for r in res:
        # if no id compute id from submit date
        if r.group("id") is None:
            td = submit_date - gtg_first_date
            id_string = str(td.days + 1)
        else:
            id_string = r.group("id")

        score_str = re.sub(r"\s", "", r.group("score"))
        err_val = score_str.find("🟩")
        guesses = err_val + 1

        logger.debug(
            f"Pattern for GuessThe.Game found with identifier {id_string} with {guesses} guesses"
        )
        pattern_results.append(
            PatternResult(game_identifier=id_string, guesses=guesses)
        )

    return pattern_results


def process_message(
    message_content: str,
    message_id: int,
    author_id: int,
) -> list[ProcessResult] | None:
    pattern_res = get_gtg_result(
        message_content, repository.snowflake_to_datetime(message_id).date()
    )
    if not pattern_res:
        return

    result_list = list[ProcessResult]()

    for pr in pattern_res:
        process_result = ProcessResult()

        if not repository.player_exists(author_id):
            repository.add_player(user_id=author_id, message_id=message_id)
            process_result.player_added = True
            process_result.message += (
                "Tack för din första guess the X postning! Du är nu registrerad som spelare!⚔️"
                + os.linesep
            )

        post_date = gtg_first_date + timedelta(days=(int(pr.game_identifier) - 1))

        if not game_exists(pr.game_identifier):
            repository.add_game(
                game_type_identifier="gtg",
                game_identifier=pr.game_identifier,
                publish_date=post_date,
            )
            process_result.game_added = True
            process_result.message += (
                f"Du var först med att posta ett resultat för omgång #{pr.game_identifier}!🏁"
                + os.linesep
            )

        if repository.result_exists(
            user_id=author_id, game_identifier=pr.game_identifier
        ):
            process_result.message += (
                f"Du har redan sparat ett resultat för omgång #{pr.game_identifier}.✋"
                + os.linesep
            )
            result_list.append(process_result)
            continue

        repository.add_result(
            user_id=author_id,
            message_id=message_id,
            game_identifier=pr.game_identifier,
            guesses=pr.guesses,
        )

        process_result.message += f"Du har registrerat ett resultat på {pr.guesses} gissning(ar) för omgång {pr.game_identifier}!👍"

        process_result.result_added = True

        result_list.append(process_result)

    return result_list
