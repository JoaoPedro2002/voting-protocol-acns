from typing import Dict

from sqlmodel import Field

from .common import PlayerInstance, SerializableType

class VoterInstance(PlayerInstance, table=True):
    __tablename__ = "voter"
    vvk: Dict | None = SerializableType()
    vck: Dict | None = SerializableType()
    voter_uuid: str = Field(unique=True)
    voter_phone: str = Field(nullable=False)
    election_uuid: str = Field(nullable=False)
    ballot_box_uuid: str = Field(nullable=False)