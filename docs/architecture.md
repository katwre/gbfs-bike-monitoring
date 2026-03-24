# Architecture

## Goal
Build an end-to-end **streaming** data pipeline for GBFS bike station availability and expose curated metrics in a dashboard with two tiles.

## Data Source
- Entry point: `https://gbfs.urbansharing.com/bergenbysykkel.no/gbfs.json`
- Streaming endpoint: `station_status.json` (updates frequently)
- Static endpoint: `station_information.json` (dimension metadata)

## End-to-End Flow
1. **Kestra** polls GBFS APIs on a schedule (30-60 seconds for station status).
2. Raw payloads are persisted to **MinIO** as the data lake (`/raw/bike_status/date=YYYY-MM-DD/`).
3. `station_status` events are published to **Kafka** (`bike_station_status_raw`).
4. A Python consumer reads Kafka events and upserts to **Postgres** staging tables.
5. **dbt** transforms staging tables into marts for analytics.
6. **Streamlit** reads marts and renders dashboard tiles.

## Core Components
- **Kafka + Zookeeper**: stream transport and topic retention.
- **Kestra**: workflow orchestration for ingestion.
- **MinIO**: object storage data lake for raw JSON snapshots.
- **Postgres**: warehouse + serving layer for dbt models and dashboard queries.
- **dbt**: transformations (staging and marts).
- **Streamlit**: lightweight dashboard frontend.
- **pgAdmin**: DB exploration and debugging.

## Data Model (Target)
### Dimension
- `dim_station`
  - `station_id`
  - `name`
  - `lat`
  - `lon`
  - `capacity`

### Fact
- `fct_station_status`
  - `station_id`
  - `timestamp`
  - `bikes_available`
  - `docks_available`

### Planned marts
- `mart_hourly_availability`
- `daily_availability`
- `low_availability_events`

## Dashboard Contract
- **Tile 1 (categorical)**: stations grouped by availability bucket (low/medium/high).
- **Tile 2 (temporal)**: bikes available over time.

## Deployment Modes
- **MVP local mode (Day 1-7)**: Docker Compose on local machine.
- **Cloud mode (stretch goal for scoring)**: same architecture deployed on cloud with Terraform-managed infrastructure.
