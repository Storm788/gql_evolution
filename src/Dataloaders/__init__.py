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
    loaders_dict = createLoaders(asyncSessionMaker)
    # Add session_maker to loaders dict for compatibility with permissions.py
    # This allows both dict access (loaders["AssetModel"]) and attribute access (loaders.session_maker)
    class LoadersDict(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.session_maker = asyncSessionMaker
    
    loaders_obj = LoadersDict(loaders_dict)
    return {
        "loaders": loaders_obj
    }

def getLoadersFromInfo(info):
    return info.context["loaders"]
