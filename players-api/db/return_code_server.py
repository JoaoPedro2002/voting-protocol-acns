from typing import Dict

from sqlmodel import Field, SQLModel, Column, Table, Relationship

from .common import PlayerInstance, SerializableType, Vote

class ReturnCodeVoteLink(SQLModel, table=True):
    __tablename__ = "return_code_vote_link"
    return_code_id: int | None = Field(default=None, foreign_key="return_code_server.id", primary_key=True)
    vote_id: int | None = Field(default=None, foreign_key="votes.id", primary_key=True)

class ReturnCodeServerInstance(PlayerInstance, table=True):
    __tablename__ = "return_code_server"
    ck: Dict | None = SerializableType()
    prf_key: str = Field(nullable=False, unique=True)
    votes: list[Vote] = Relationship(link_model=ReturnCodeVoteLink)