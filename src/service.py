from loguru import logger

from src import repository
from src.utils import Participation


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
