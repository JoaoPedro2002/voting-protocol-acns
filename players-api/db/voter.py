from typing import Dict

from sqlmodel import Field

from .common import PlayerInstance, SerializableType, ListType

class VoterInstance(PlayerInstance, table=True):
    __tablename__ = "voter"
    # id: int = Field(primary_key=True)
    vvk: Dict | None = SerializableType()
    vck: Dict | None = SerializableType()
    return_code_tables: list[dict] = ListType()