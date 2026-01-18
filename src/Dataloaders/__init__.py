from functools import cache
from typing import Callable
from sqlalchemy.ext.asyncio import AsyncSession
from uoishelpers.dataloaders import createIdLoader

from src.DBDefinitions import (
    BaseModel,
    EventModel,
    EventInvitationModel,
    AssetModel,
    AssetLoanModel,
    AssetInventoryRecordModel
)

@cache
def createLoaders(asyncSessionMaker: Callable[[], AsyncSession]):
    """
    Creates and caches dataloaders for GraphQL models.
    asyncSessionMaker should be a callable that returns an AsyncSession instance.
    """
    return {
        "EventModel": createIdLoader(asyncSessionMaker, EventModel),
        "EventInvitationModel": createIdLoader(asyncSessionMaker, EventInvitationModel),
        "AssetModel": createIdLoader(asyncSessionMaker, AssetModel),
        "AssetLoanModel": createIdLoader(asyncSessionMaker, AssetLoanModel),
        "AssetInventoryRecordModel": createIdLoader(asyncSessionMaker, AssetInventoryRecordModel),
    }

def createLoadersContext(asyncSessionMaker: Callable[[], AsyncSession]):
    """
    Wraps the dataloader factory for use in the GraphQL context.
    asyncSessionMaker should be a callable that returns an AsyncSession instance.
    """
    return {
        "loaders": createLoaders(asyncSessionMaker)
    }

def getLoadersFromInfo(info):
    return info.context["loaders"]
