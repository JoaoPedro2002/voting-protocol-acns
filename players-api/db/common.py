from typing import Dict

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON

STATES = ["setup", "registration", "voting", "counting", "finished"]


SerializableType = lambda **args: Field(default_factory=dict, sa_type=JSON, **args)
ListType = lambda **args: Field(default_factory=list, sa_type=JSON, **args)

class PlayerInstance(SQLModel, table=False):
    __abstract__ = True
    id: int = Field(primary_key=True)
    pk: Dict | None = SerializableType(nullable=True)
    auditors_urls: list[str] = ListType()
    shuffle_server_url: str = Field(nullable=False)
    return_code_server_url: str = Field(nullable=False)
    ballot_box_url: str = Field(nullable=False)
    election_uuid: str = Field(nullable=False, unique=True)
    ballot_box_uuid: str = Field(nullable=False, unique=True)
    state: str = Field(nullable=False, default="setup")

    def next_state(self):
        self.set_state(STATES.index(self.state) + 1)

    def set_state(self, state):
        if state >= len(STATES):
            self.state = "finished"
        self.state = STATES[state]


class Vote(SQLModel, table=True):
    __tablename__ = "votes"
    id: int = Field(primary_key=True)
    voter_id: str = Field(nullable=False)
    election_uuid: str = Field(nullable=False)
    questions: list["Question"] = Relationship(back_populates="vote")


class Question(SQLModel, table=True):
    __tablename__ = "questions"
    id: int = Field(primary_key=True)
    ev: Dict = SerializableType()
    proof: Dict = SerializableType()

    vote_id: int = Field(foreign_key="votes.id")
    vote: Vote = Relationship(back_populates="questions")

class VoterPublicData(SQLModel, table=True):
    __tablename__ = "voters_public_data"
    id: int = Field(primary_key=True)
    voter_uuid: str = Field(nullable=False, unique=True)
    voter_email: str = Field(nullable=False)
    vvk: Dict = SerializableType()
    election_uuid: str = Field(nullable=False)