import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .BaseModel import BaseModel, UUIDFKey, IDType


class AssetModel(BaseModel):
    __tablename__ = "assets_evolution"

    name: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    inventory_code: Mapped[Optional[str]] = mapped_column(index=True, default=None, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)

    owner_group_id: Mapped[Optional[IDType]] = UUIDFKey(ForeignKey("groups.id"), default=None, nullable=True, comment="Group owning the asset")
    custodian_user_id: Mapped[Optional[IDType]] = UUIDFKey(ForeignKey("users.id"), default=None, nullable=True, comment="User responsible for the asset")

    location: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)

    inventory_records = relationship(
        "AssetInventoryRecordModel", back_populates="asset", uselist=True, cascade="save-update"
    )
    loans = relationship(
        "AssetLoanModel", back_populates="asset", uselist=True, cascade="save-update"
    )


class AssetInventoryRecordModel(BaseModel):
    __tablename__ = "asset_inventory_records_evolution"

    asset_id: Mapped[Optional[IDType]] = mapped_column(ForeignKey("assets_evolution.id"), default=None, nullable=True, index=True)
    record_date: Mapped[Optional[datetime.datetime]] = mapped_column(default=None, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)
    checked_by_user_id: Mapped[Optional[IDType]] = UUIDFKey(ForeignKey("users.id"), default=None, nullable=True)

    asset = relationship("AssetModel", viewonly=True, primaryjoin="AssetInventoryRecordModel.asset_id==AssetModel.id", uselist=False)


class AssetLoanModel(BaseModel):
    __tablename__ = "asset_loans_evolution"

    asset_id: Mapped[Optional[IDType]] = mapped_column(ForeignKey("assets_evolution.id"), default=None, nullable=True, index=True)
    borrower_user_id: Mapped[Optional[IDType]] = UUIDFKey(ForeignKey("users.id"), default=None, nullable=True)
    startdate: Mapped[Optional[datetime.datetime]] = mapped_column(default=None, nullable=True)
    enddate: Mapped[Optional[datetime.datetime]] = mapped_column(default=None, nullable=True)
    returned_date: Mapped[Optional[datetime.datetime]] = mapped_column(default=None, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(default=None, nullable=True)

    asset = relationship("AssetModel", viewonly=True, primaryjoin="AssetLoanModel.asset_id==AssetModel.id", uselist=False)

