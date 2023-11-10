from dataclasses import dataclass

from pydantic import BaseModel
from datetime import datetime, date


class Player(BaseModel):
    id: int
    join_date: datetime
    id_hash: str
    id_enc: str
    active: bool
    visible: bool


@dataclass
class PlayerDisplay:
    name: str
    join_date: date
