from sqlalchemy.orm import DeclarativeBase

from uoishelpers.resolvers import createDBResolvers
from functools import cache


class BaseModel(DeclarativeBase):

    @property
    @cache
    def resolvers(self):
        return createDBResolvers(self)
    
    pass
