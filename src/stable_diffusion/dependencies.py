from fastapi import Depends
from sqlalchemy.orm import Session

from ..database import get_db
from .services import EntryService


def get_entry_service(db: Session = Depends(get_db)):
    return EntryService(db)
