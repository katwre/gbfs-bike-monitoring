import os
import json
from datetime import datetime, timezone

from kafka import KafkaConsumer
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    DateTime,
    JSON,
    insert,
)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "bike_station_status_raw")
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "0"))

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "gbfs_monitoring")
POSTGRES_USER = os.getenv("POSTGRES_USER", "gbfs")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "gbfs")


def get_engine():
    db_url = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    return create_engine(db_url)


def define_table(metadata: MetaData) -> Table:
    return Table(
        "station_status_raw",
        metadata,
        Column("station_id", String, nullable=False),
        Column("bikes_available", Integer),
        Column("docks_available", Integer),
        Column("event_time", DateTime(timezone=True), nullable=False),
        Column("ingested_at", DateTime(timezone=True), nullable=False),
        Column("raw_payload", JSON, nullable=False),
        schema="staging",
    )


def build_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id="gbfs-postgres-loader",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )


def transform_message(payload: dict) -> dict:
    timestamp = payload["timestamp"]
    event_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    return {
        "station_id": payload["station_id"],
        "bikes_available": payload["num_bikes_available"],
        "docks_available": payload["num_docks_available"],
        "event_time": event_time,
        "ingested_at": datetime.now(timezone.utc),
        "raw_payload": payload,
    }

def insert_record(engine, table: Table, record: dict) -> None:
    stmt = insert(table).values(**record)

    with engine.begin() as connection:
        connection.execute(stmt)


def main():
    engine = get_engine()
    metadata = MetaData()
    table = define_table(metadata)

    # create table if it does not exist; staging schema is created by SQL init scripts
    metadata.create_all(engine)

    consumer = build_consumer()

    for i, message in enumerate(consumer, start=1):

        payload = message.value

        try:
            record = transform_message(payload)
            insert_record(engine, table, record)

            # commit Kafka offset only after DB insert succeeds
            consumer.commit()

            print(f"Inserted station_id={record['station_id']} at {record['event_time']}")
            if MAX_MESSAGES and i >= MAX_MESSAGES:
                print(f"Reached MAX_MESSAGES={MAX_MESSAGES}, stopping consumer.")
                break
        except Exception as exc:
            print(f"Failed to process message: {exc}")

    consumer.close()


if __name__ == "__main__":
    main()