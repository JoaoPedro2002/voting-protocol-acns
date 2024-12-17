from typing import Dict

from sqlmodel import Field, SQLModel

from .common import PlayerInstance, SerializableType

class ShufflerServerInstance(PlayerInstance, table=True):
    __tablename__ = "shuffle_server"
    # id: int = Field(primary_key=True)
    dk: Dict = SerializableType()