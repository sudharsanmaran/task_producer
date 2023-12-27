import json
import logging
import os

from celery import Celery


logging.basicConfig(level=logging.INFO)

logging.info("Celery worker not started")

app = Celery("tasks", broker=os.getenv('RABBITMQ_BROKER_URL'))

logging.info("Celery worker started")


@app.task(name="update_database")
def update_database(message):
    from src.database import ScopedSession
    from src.stable_diffusion.services import EntryService
    from src.stable_diffusion.constants import Status

    # Parse the message and extract the data to be updated in the database
    data = json.loads(message)
    session = ScopedSession()
    entry_service = EntryService(session)
    entry = entry_service.get_by_primary_key(data["id"])
    if entry is None:
        logging.error(f'Entry with id {data["id"]} not found')
        return
    entry.response_data = data["response"]
    print(" status recived #########", data['status'])
    if data["status"] == 'failed':
        entry.status = Status.FAILED
    else:
        entry.status = Status.COMPLETED
    entry_service.update(entry)
    logging.info(f"Updating entry {entry} with status {data}")
