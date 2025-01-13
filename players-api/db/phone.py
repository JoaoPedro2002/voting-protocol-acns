from sqlmodel import Field, SQLModel, Relationship, Column, ARRAY, String
from sqlalchemy.ext.mutable import MutableList
from .common import ListType


class PhoneInstance(SQLModel, table=True):
    __tablename__ = "phone"
    id: int | None = Field(default=None, primary_key=True)
    voter_uuid: str = Field(nullable=False)
    rct: list[dict] = ListType()
    expected_return_codes: list[str] = ListType()