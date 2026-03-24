import json
import os
from datetime import datetime, timezone

import boto3
import requests
from kafka import KafkaProducer


GBFS_STATION_STATUS_URL = os.getenv(
    "GBFS_STATION_STATUS_URL",
    "https://gbfs.urbansharing.com/bergenbysykkel.no/station_status.json",
)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "gbfs-raw")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "bike_station_status_raw")


def fetch_station_status() -> dict:
    response = requests.get(GBFS_STATION_STATUS_URL, timeout=30)
    response.raise_for_status()
    return response.json()


def write_raw_to_minio(payload: dict, snapshot_at: datetime) -> str:
    s3_client = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )

    existing_buckets = {bucket["Name"] for bucket in s3_client.list_buckets().get("Buckets", [])}
    if MINIO_BUCKET not in existing_buckets:
        s3_client.create_bucket(Bucket=MINIO_BUCKET)

    object_key = (
        f"raw/bike_status/date={snapshot_at:%Y-%m-%d}/"
        f"hour={snapshot_at:%H}/snapshot_{snapshot_at:%Y%m%dT%H%M%SZ}.json"
    )
    s3_client.put_object(
        Bucket=MINIO_BUCKET,
        Key=object_key,
        Body=json.dumps(payload).encode("utf-8"),
        ContentType="application/json",
    )
    return object_key


def publish_status_to_kafka(payload: dict) -> int:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda key: str(key).encode("utf-8"),
    )

    last_reported = payload.get("data", {}).get("last_updated")
    stations = payload.get("data", {}).get("stations", [])
    count = 0

    for station in stations:
        event = {
            "station_id": station.get("station_id"),
            "num_bikes_available": station.get("num_bikes_available"),
            "num_docks_available": station.get("num_docks_available"),
            "timestamp": station.get("last_reported") or last_reported,
        }
        station_id = event["station_id"]
        if station_id is None:
            continue

        producer.send(KAFKA_TOPIC, key=station_id, value=event)
        count += 1

    producer.flush()
    producer.close()
    return count


def main() -> None:
    snapshot_at = datetime.now(timezone.utc)
    payload = fetch_station_status()
    object_key = write_raw_to_minio(payload, snapshot_at)
    published_count = publish_status_to_kafka(payload)

    print(
        json.dumps(
            {
                "status": "ok",
                "bucket": MINIO_BUCKET,
                "object_key": object_key,
                "kafka_topic": KAFKA_TOPIC,
                "published_messages": published_count,
            }
        )
    )


if __name__ == "__main__":
    main()
