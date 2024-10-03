import sqlalchemy
import datetime
from sqlalchemy.schema import Column
from sqlalchemy import Uuid, String, DateTime, ForeignKey
from sqlalchemy.orm import column_property

from .baseDBModel import BaseModel
from .uuid import uuid

class EventModel(BaseModel):
    __tablename__ = "events"

    id = Column(Uuid, primary_key=True, comment="primary key", default=uuid)
    name = Column(String, comment="name / label of the event")

    startdate = Column(DateTime, comment="when the event should start")
    enddate = Column(DateTime, comment="when the event should end")
    duration = column_property(enddate-startdate)


    masterevent_id = Column(
        ForeignKey("events.id"), index=True, nullable=True,
        comment="event which owns this event")

    lastchange = Column(DateTime, default=datetime.datetime.now)
