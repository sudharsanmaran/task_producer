import json
from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import Mapped

from src.stable_diffusion.constants import Status

from ..database import Base

from ..mixins import TimestampMixin, UUIDMixin


class Entry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "entries"

    user_email: Mapped[str] = Column(String, nullable=False, index=True)
    status: Status = Column(String, nullable=False)
    request_data: Mapped[JSON] = Column(JSON, nullable=False)
    response_data: Mapped[JSON] = Column(JSON)
    webhook_url: Mapped[str] = Column(String, nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_email": self.user_email,
            "status": self.status,
            "request_data": self.request_data,
            "response_data": self.response_data,
            "webhook_url": self.webhook_url,
        }

    def to_json(self):
        return json.dumps(self.to_dict())
