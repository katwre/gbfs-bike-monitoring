CREATE TABLE IF NOT EXISTS raw.station_information_raw (
    ingestion_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system TEXT,
    payload JSONB
);

CREATE TABLE IF NOT EXISTS raw.station_status_raw (
    ingestion_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system TEXT,
    payload JSONB
);

CREATE TABLE IF NOT EXISTS staging.station_information (
    station_id TEXT PRIMARY KEY,
    name TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    capacity INTEGER,
    rental_methods TEXT[],
    last_seen_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS staging.station_status_raw (
    station_id TEXT,
    bikes_available INTEGER,
    docks_available INTEGER,
    event_time BIGINT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_payload JSONB,
    UNIQUE (station_id, event_time)
);

CREATE TABLE IF NOT EXISTS staging.station_status (
    station_id TEXT,
    last_reported BIGINT,
    num_bikes_available INTEGER,
    num_docks_available INTEGER,
    is_installed INTEGER,
    is_renting INTEGER,
    is_returning INTEGER,
    ingestion_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);