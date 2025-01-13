from sqlmodel import Field, SQLModel

from .common import PlayerInstance, ListType


class AuditorInstance(PlayerInstance, table=True):
    __tablename__ = "auditor"
    election_uuid: str = Field(nullable=False, unique=True)
    ballot_box_uuid: str = Field(nullable=False, unique=True)
    # counting
    shuffle_proofs: list = ListType(nullable=True)
    ballots: list = ListType(nullable=True)
    # verification
    evs: list = ListType(nullable=True)
    proofs: list = ListType(nullable=True)