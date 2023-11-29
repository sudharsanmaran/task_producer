import json
import logging

from celery import Celery


logging.basicConfig(level=logging.INFO)

logging.info("Celery worker not started")

app = Celery("tasks", broker="amqp://guest:guest@localhost//")

logging.info("Celery worker started")


@app.task(name="update_database")
def update_database(message):
    from src.database import ScopedSession
    from src.stable_diffusion.services import EntryService
    from src.stable_diffusion.constants import Status

    # Parse the message and extract the data to be updated in the database
    data = json.loads(message)
    print(data, "celery worker")
    session = ScopedSession()
    entry_service = EntryService(session)
    entry = entry_service.get_by_primary_key(data["id"])
    entry.response_data = data["response"]
    entry.status = Status.COMPLETED
    entry_service.update(entry)
    print(data, "celery worker", entry)
    logging.info(f"Updating entry {entry} with status {data}")
