import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .BaseModel import BaseModel, UUIDFKey, IDType


class AssetInventoryRecordModel(BaseModel):
    __tablename__ = "asset_inventory_records_evolution"

    asset_id: Mapped[Optional[IDType]] = mapped_column(
        ForeignKey("assets_evolution.id"), default=None, nullable=True, index=True
    )
    record_date: Mapped[Optional[datetime.datetime]] = mapped_column(default=None, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    checked_by_user_id: Mapped[Optional[IDType]] = UUIDFKey(
        ForeignKey("users.id"), default=None, nullable=True
    )

    asset = relationship(
        "AssetModel",
        viewonly=True,
        primaryjoin="AssetInventoryRecordModel.asset_id==AssetModel.id",
        uselist=False,
    )
