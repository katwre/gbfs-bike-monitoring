#!/usr/bin/env python3
"""
Load raw GBFS snapshots from MinIO and insert into Postgres staging.
Each snapshot contains all stations' status at one point in time.
"""

import json
import os
from datetime import datetime
from sqlalchemy import create_engine, text
import boto3


def get_engine():
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://gbfs:gbfs@postgres:5432/gbfs_monitoring"
    )
    return create_engine(db_url)


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://minio:9000"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY", "minio"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY", "minio123"),
    )


def load_snapshots_from_minio(s3_client, bucket="gbfs-raw", prefix="raw/bike_status/"):
    """List all raw snapshot objects from MinIO."""
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    
    objects = []
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                if obj['Key'].endswith('.json'):
                    objects.append(obj['Key'])
    
    return sorted(objects)


def parse_snapshot_json(json_bytes):
    """Parse raw GBFS snapshot and yield (timestamp, station_data) tuples."""
    try:
        data = json.loads(json_bytes.decode('utf-8'))
        
        # Snapshot-level timestamp
        snapshot_ts = data.get('last_updated')
        
        # Extract stations array
        stations = data.get('data', {}).get('stations', [])
        
        for station in stations:
            yield {
                'station_id': station.get('station_id'),
                'bikes_available': station.get('num_bikes_available'),
                'docks_available': station.get('num_docks_available'),
                'event_time': snapshot_ts,  # Unix timestamp
                'raw_payload': json.dumps(station),  # Store individual station JSON
            }
    except json.JSONDecodeError:
        print(f"Failed to decode JSON")
        return


def insert_records(engine, records):
    """Batch insert transformed records into staging table."""
    if not records:
        return
    
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO staging.station_status_raw 
                (station_id, bikes_available, docks_available, event_time, ingested_at, raw_payload)
                VALUES (:station_id, :bikes_available, :docks_available, 
                        :event_time, now(), :raw_payload)
                ON CONFLICT DO NOTHING
            """),
            records
        )
        conn.commit()


def main():
    engine = get_engine()
    s3_client = get_s3_client()
    
    # Load object list
    print("Fetching snapshot list from MinIO...")
    objects = load_snapshots_from_minio(s3_client)
    print(f"Found {len(objects)} snapshots")
    
    # Process each snapshot
    processed = 0
    total_records = 0
    batch_size = 1000
    batch = []
    
    for obj_key in objects:
        try:
            # Fetch snapshot from MinIO
            response = s3_client.get_object(Bucket='gbfs-raw', Key=obj_key)
            json_bytes = response['Body'].read()
            
            # Parse and extract stations
            for record in parse_snapshot_json(json_bytes):
                if record:
                    batch.append(record)
                    total_records += 1
            
            # Batch insert every N records
            if len(batch) >= batch_size:
                insert_records(engine, batch)
                print(f"  Processed {processed + 1}/{len(objects)} snapshots ({total_records} records)")
                batch = []
            
            processed += 1
        
        except Exception as e:
            print(f"Error processing {obj_key}: {e}")
            continue
    
    # Final batch
    if batch:
        insert_records(engine, batch)
    
    print(f"\n✓ Loaded {total_records} records from {processed} snapshots")


if __name__ == "__main__":
    main()
