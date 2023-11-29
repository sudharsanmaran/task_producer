from .models import Entry
from ..base_service import ListCreateUpdateRetrieveDeleteService
from sqlalchemy.orm import session


class EntryService(ListCreateUpdateRetrieveDeleteService):
    def __init__(self, db: session):
        super().__init__(db, Entry, 'id')
