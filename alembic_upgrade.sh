#!/bin/bash


# Generate a new Alembic revision.
# alembic revision --autogenerate -m 'init'

# Upgrade the database.
# alembic upgrade head

uvicorn src.main:app --host=0.0.0.0 --port=8001 --reload --log-level=info