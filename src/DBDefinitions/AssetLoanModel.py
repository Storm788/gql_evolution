import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .BaseModel import BaseModel, UUIDFKey, IDType


class AssetLoanModel(BaseModel):
    __tablename__ = "asset_loans_evolution"

    asset_id: Mapped[Optional[IDType]] = mapped_column(
        ForeignKey("assets_evolution.id"), default=None, nullable=True, index=True
    )
    borrower_user_id: Mapped[Optional[IDType]] = UUIDFKey(
        ForeignKey("users.id"), default=None, nullable=True
    )
    startdate: Mapped[Optional[datetime.datetime]] = mapped_column(default=None, nullable=True)
    enddate: Mapped[Optional[datetime.datetime]] = mapped_column(default=None, nullable=True)
    returned_date: Mapped[Optional[datetime.datetime]] = mapped_column(default=None, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)

    asset = relationship(
        "AssetModel",
        viewonly=True,
        primaryjoin="AssetLoanModel.asset_id==AssetModel.id",
        uselist=False,
    )
