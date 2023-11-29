import logging
import uuid
from fastapi import HTTPException
from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.query import Query
from typing import List, Type


logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)


class ListCreateUpdateRetrieveDeleteService:
    def __init__(self, db: Session, model_class: Type, primary_key_name: str):
        self.db = db
        self.model_class = model_class
        self.primary_key_name = primary_key_name
        self.logger = logger

    @staticmethod
    def handle_sqlalchemy_error(error: SQLAlchemyError, model_name: str):
        error_message = "An error occurred with the database."
        logger.error(f"Error with model {model_name}: {error}")
        raise HTTPException(status_code=400, detail=error_message)

    def get(self, **kwargs) -> Query:
        try:
            stmt = select(self.model_class).where(
                and_(
                    *(
                        getattr(self.model_class, key) == value
                        for key, value in kwargs.items()
                    )
                )
            )

            with self.db:
                results = self.db.execute(stmt).scalar_one()
            return results
        except NoResultFound:
            logger.info(
                f"No result found for model {self.model_class} with parameters {kwargs}"
            )
            return None

    def get_by_primary_key(self, primary_key_value) -> Query:
        try:
            stmt = select(self.model_class).where(
                getattr(self.model_class, self.primary_key_name) == primary_key_value
            )

            with self.db:
                result = self.db.execute(stmt).scalar_one()
            return result
        except NoResultFound:
            logger.info(
                f"No result found for model {self.model_class} with primary key {primary_key_value}"
            )
            return None

    def get_all(self, **kwargs) -> Query:
        try:
            stmt = select(self.model_class).where(
                and_(
                    *(
                        getattr(self.model_class, key) == value
                        for key, value in kwargs.items()
                    )
                )
            )

            with self.db:
                results = self.db.execute(stmt).scalars().all()
            return results
        except NoResultFound:
            logger.info(
                f"No result found for model {self.model_class} with parameters {kwargs}"
            )
            return None

    def list(self, limit: int = 10, offset: int = 0, **kwargs) -> List[Query]:
        try:
            stmt = (
                select(self.model_class)
                .where(
                    and_(
                        *(
                            getattr(self.model_class, key) == value
                            for key, value in kwargs.items()
                        )
                    )
                )
                .offset(offset)
                .limit(limit)
            )

            with self.db:
                results = self.db.execute(stmt).scalars().all()
            return results
        except SQLAlchemyError as e:
            self.handle_sqlalchemy_error(e, self.model_class)

    def create(self, obj) -> Query:
        try:
            obj = self.model_class(**obj)
            with self.db.begin():
                self.db.add(obj)
                self.db.flush()
                self.db.refresh(obj)
            logger.info(f"Created new {self.model_class} with parameters {obj}")
            return obj
        except (IntegrityError, SQLAlchemyError) as e:
            self.handle_sqlalchemy_error(e, self.model_class)

    def update(self, obj) -> Query:
        try:
            with self.db.begin():
                self.db.merge(obj)
            logger.info(f"Updated {self.model_class} with parameters {obj}")
            return obj
        except (IntegrityError, SQLAlchemyError) as e:
            self.handle_sqlalchemy_error(e, self.model_class)

    # def bulk_update(self, objs: List) -> List[Query]:
    #     try:
    #         with self.db.begin():
    #             self.db.bulk_update_mappings(self.model_class, objs)
    #             self.db.flush()
    #             self.db.refresh(objs)
    #         logger.info(f"Bulk updated {len(objs)} {self.model_class} records")
    #         return objs
    #     except (IntegrityError, SQLAlchemyError) as e:
    #         self.handle_sqlalchemy_error(e, self.model_class)

    def create_or_update(self, obj, lookup_field) -> Query:
        try:
            existing_record = self.get(**{lookup_field: obj[lookup_field]})
            if existing_record:
                for key, value in obj.items():
                    setattr(existing_record, key, value)
            with self.db.begin():
                merged = self.db.merge(existing_record or self.model_class(**obj))
                self.db.flush()
                self.db.refresh(merged)
            logger.info(f"Updated {self.model_class} with parameters {obj}")
            return merged
        except (IntegrityError, SQLAlchemyError) as e:
            self.handle_sqlalchemy_error(e, self.model_class)

    # def bulk_create_or_update(self, objs: List[dict], lookup_field: str) -> None:
    #     try:
    #         lookup_values = [obj[lookup_field] for obj in objs]

    #         existing_records = (
    #             self.db.query(self.model_class)
    #             .filter(getattr(self.model_class, lookup_field).in_(lookup_values))
    #             .all()
    #         )

    #         existing_records_dict = {
    #             getattr(record, lookup_field): record for record in existing_records
    #         }

    #         updates = []
    #         inserts = []

    #         for obj in objs:
    #             record = existing_records_dict.get(obj[lookup_field])
    #             if record:
    #                 for key, value in obj.items():
    #                     setattr(record, key, value)
    #                 updates.append(record)
    #             else:
    #                 inserts.append(obj)

    #         self.db.bulk_update_mappings(
    #             self.model_class, [dict(u) for u in updates]
    #         )
    #         self.db.bulk_save_objects(inserts)

    #         logger.info(
    #             f"Bulk created or updated {len(objs)} {self.model_class} records"
    #         )
    #     except (IntegrityError, SQLAlchemyError) as e:
    #         self.handle_sqlalchemy_error(e, self.model_class)

    def delete(self, obj) -> None:
        try:
            with self.db.begin():
                self.db.delete(obj)
            logger.info(f"Deleted {self.model_class} with parameters {obj}")
        except (IntegrityError, SQLAlchemyError) as e:
            self.handle_sqlalchemy_error(e, self.model_class)

    def get_unset_deafult_stmt(self, user_id: uuid.UUID):
        # flake8: noqa
        return (
            update(self.model_class)
            .where(
                and_(
                    getattr(self.model_class, "user_id") == user_id,
                    getattr(self.model_class, "default") == True,
                )
            )
            .values(default=False)
        )

    def unset_and_set_default(self, user_id: uuid.UUID, email: str):
        unset_stmt = self.get_unset_deafult_stmt(user_id)
        set_stmt = (
            update(self.model_class)
            .where(
                and_(
                    self.model_class.user_id == user_id,
                    self.model_class.email == email,
                )
            )
            .values(default=True)
        )

        with self.db.begin():
            self.db.execute(unset_stmt)
            self.db.execute(set_stmt)

    def unset_default_and_create_or_update(self, obj) -> Query:
        unset_stmt = self.get_unset_deafult_stmt(obj["user_id"])
        try:
            existing_record = self.get(user_id=obj["user_id"], email=obj["email"])
            if existing_record:
                for key, value in obj.items():
                    setattr(existing_record, key, value)
            with self.db.begin():
                self.db.execute(unset_stmt)
                merged = self.db.merge(existing_record or self.model_class(**obj))
                self.db.flush()
                self.db.refresh(merged)
            self.logger.info(
                f"Created or updated {self.model_class} with parameters {obj}"
            )
            return merged
        except (IntegrityError, SQLAlchemyError) as e:
            self.handle_sqlalchemy_error(e, self.model_class)
