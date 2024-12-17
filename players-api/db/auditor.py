from sqlmodel import Field, SQLModel

from .common import PlayerInstance

class AuditorInstance(PlayerInstance, table=True):
    __tablename__ = "auditor"