import uuid
from sqlalchemy import Column, DateTime, func, Uuid
from sqlalchemy.orm import Mapped


class TimestampMixin:
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        index=True,
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = Column(
        Uuid, primary_key=True, default=lambda: uuid.uuid4(), index=True
    )
