# https://strawberry.rocks/docs/types/scalars#custom-scalars
# from typing import NewType
import datetime
import strawberry

timedelta = strawberry.scalar(
    # NewType("TimeDelta", float),
    datetime.timedelta,
    name="timedelta",
    serialize=lambda v: v.total_seconds() / 60,
    parse_value=lambda v: datetime.timedelta(minutes=v),
)