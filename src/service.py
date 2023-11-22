import asyncio

from loguru import logger

from src import repository
from src.models import PlayerStreak
from src.utils import Participation


def get_all_players():
    return repository.get_all_players(active=True, inactive=True)


def toggle_player_visible(user_id) -> bool:
    current_vis_val = repository.get_participation_value(
        user_id, participation_type=Participation.VISIBLE
    )
    logger.info(f"Current vis val {current_vis_val}")
    updated_player = repository.update_player(
        user_id=user_id, visibility=not current_vis_val
    )

    logger.info(
        f"Player with user id: {user_id} has visible attribute set to {updated_player.visible}"
    )

    return updated_player.visible


def toggle_player_active(user_id) -> bool:
    current_active_val = repository.get_participation_value(
        user_id, participation_type=Participation.ACTIVE
    )
    updated_player = repository.update_player(
        user_id=user_id, active=not current_active_val
    )

    logger.info(
        f"Player with user id: {user_id} active attribute set to {updated_player.active}"
    )

    return updated_player.active


def generate_streak_chart() -> list[PlayerStreak]:
    active_players = repository.get_all_players()
    streak_results = list[PlayerStreak]()

    for p in active_players:
        if p.visible:
            streak_results.append(repository.get_current_streak(p.user_id))

    streak_results.sort()

    return streak_results


def is_player_visible(user_id: int) -> bool:
    p = repository.get_player(user_id)
    return p.visible


def is_player_active(user_id: int) -> bool:
    p = repository.get_player(user_id)
    return p.active


async def main():
    pass


if __name__ == "__main__":
    asyncio.run(main())
