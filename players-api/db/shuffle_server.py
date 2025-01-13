from typing import Dict

from sqlmodel import Field, SQLModel

from .common import PlayerInstance, SerializableType

class ShuffleServerInstance(PlayerInstance, table=True):
    __tablename__ = "shuffle_server"
    # id: int = Field(primary_key=True)
    dk: Dict = SerializableType()
    election_uuid: str = Field(nullable=False, unique=True)
    ballot_box_uuid: str = Field(nullable=False, unique=True)