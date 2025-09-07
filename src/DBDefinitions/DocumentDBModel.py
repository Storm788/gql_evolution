import typing
import datetime
import dataclasses
import sqlalchemy
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, synonym

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, column_property
from pgvector.sqlalchemy import Vector

from .BaseModel import BaseModel, UUIDColumn, UUIDFKey, IDType

###########################################################################################################################
#
# zde definujte sve SQLAlchemy modely
# je-li treba, muzete definovat modely obsahujici jen id polozku, na ktere se budete odkazovat
#
###########################################################################################################################
class DocumentModel(BaseModel):
    __tablename__ = "document_evolution"

    path_attribute_name = "path"
    parent_attribute_name = "masterdocument"
    parent_id_attribute_name = "masterdocument_id"
    children_attribute_name = "subdocuments"

    # Materialized path technique
    path: Mapped[str] = mapped_column(
        index=True,
        nullable=True,
        default=None,
        comment="Materialized path technique, not implemented"
    )

    name: Mapped[str] = mapped_column(default=None, nullable=True)
    name_en: Mapped[str] = mapped_column(default=None, nullable=True)
    description: Mapped[str] = mapped_column(default=None, nullable=True)
    url: Mapped[str] = mapped_column(default=None, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    embedding_location: Mapped[str] = mapped_column(default=None, nullable=True)
    
    # the real column in the DB
    masterdocument_id: Mapped[IDType] = mapped_column(
        ForeignKey("documents_evolution.id"),
        nullable=True,
        default=None,
        index=True,
    )

    masterdocument = relationship(
        "DocumentModel",
        viewonly=True, 
        remote_side="DocumentModel.id",
        uselist=False,
        back_populates="subdocuments",
    ) # https://docs.sqlalchemy.org/en/20/orm/self_referential.html

    subdocuments = relationship(
        "DocumentModel", 
        back_populates="masterdocument",
        uselist=True,
        init=True,
        cascade="save-update"
    ) # https://docs.sqlalchemy.org/en/20/orm/self_referential.html
    # https://docs.sqlalchemy.org/en/20/_modules/examples/materialized_paths/materialized_paths.html
