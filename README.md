
# GBFS Bike Monitoring

This project ingests GBFS bike station data every minute using Kestra, writes raw events to MinIO and Kafka, loads curated records into PostgreSQL, transforms them with dbt, and serves a two-tile Streamlit dashboard (dockerized with docker compose).

City-bike availability changes quickly, but raw GBFS feeds are not directly analytics-friendly. The goal is to build a reproducible pipeline that turns raw bike station events into dashboard-ready metrics for station availability distribution and time trends.

Dashboard preview:
1. Categorical tile: station counts by availability bucket (low/medium/high)
2. Temporal tile: bikes available over time


More info on urban sharing in Bergen:
- https://urbansharing.com/
- https://bergenbysykkel.no/en/

<figure>
<p align="center">
  <img src="./img/dashboard.gif" alt="Logo" width="900">
</p>
  <figcaption align="center"><b>Figure.</b> A dashboard preview.</figcaption>
</figure>


> This application was developed as part of the [Data engineering Zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp/tree/main) by [DataTalks.Club](https://datatalks.club/), a free course focused on building production-ready data pipelines.


## Tech stack

 • Docker Compose (to run services in one app stack)

 • Kafka + Zookeeper (event stream/message bus and ZooKeeper for metadata/coordination)

 • Kestra (orchestrator)

 • MinIO (data lake = raw storage)

 • PostgreSQL (warehouse) • SQL

 • dbt (transformations)

 • Streamlit (dashboard) • plotly


### Core MVP

The flow of the application:
```text
- GBFS
  ↓
- Kestra
  ↓
- Kafka + MinIO
  ↓
- Python consumer
  ↓
- Postgres
  ↓
- dbt
  ↓
- Streamlit (2 tiles: availability category and bikes of over time)
  ↓
  Nice extras in progress:
- GitHub Actions (CI/CD) + Cloud deployment (Terraform)
```


## Data source
- GBFS root feed: https://gbfs.urbansharing.com/bergenbysykkel.no/gbfs.json
- Streaming endpoint: https://gbfs.urbansharing.com/bergenbysykkel.no/station_status.json
- Static metadata: https://gbfs.urbansharing.com/bergenbysykkel.no/station_information.json

I chose this dataset, because:
- No API key required
- JSON format
- Frequent updates (~10 seconds)
- Standardized GBFS schema

## Repository structure
```text
gbfs-bike-monitoring/
├── README.md
├── docker-compose.yml
├── app/
│   ├── consumers/
│   ├── loaders/
│   ├── models/
│   ├── producer_helpers/
│   └── utils/
├── dashboard/
│   ├── app.py
│   └── pages/
├── data/
│   └── sample/
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   └── marts/
│   └── profiles/
├── docs/
│   ├── architecture.md
│   └── diagrams/
├── infra/
│   └── terraform/
├── kestra/
│   └── flows/
├── sql/
│   ├── init/
│   └── queries/
└── tests/
```

## How to run locally with Docker

Start services:
```bash
docker-compose up -d
```

Check running containers:
```bash
docker-compose ps
```

Stop services:
```bash
docker-compose down
```

Local endpoints:
- Streamlit dashboard: http://localhost:8501
- Kestra: http://localhost:8080
- MinIO API: http://localhost:9000
- MinIO Console: http://localhost:9001
- pgAdmin: http://localhost:5050
- Postgres: localhost:5433
- Kafka broker: localhost:9092


### To run ingestion once and immediately:
Use the Python ingestor once to fetch current station status, save raw JSON to MinIO, and publish station events to Kafka:

In MinIO Console (`http://localhost:9001`, user: `minio`, password: `minio123`):
1. Create a bucket named `gbfs-raw`.

And then paste:
```bash
docker run --rm --network gbfs-bike-monitoring_default -v "$PWD":/work -w /work python:3.11-slim \
	bash -lc "pip install -r app/producer_helpers/requirements.txt && python app/producer_helpers/gbfs_to_minio_kafka.py"
```

Expected result: JSON output with `status: ok`, `object_key`, and `published_messages`.

### To run ingestion in a scheduled way with Kestra:

A Kestra flow scaffold is provided at [kestra/flows/gbfs_station_status_to_minio_kafka.yml](kestra/flows/gbfs_station_status_to_minio_kafka.yml).

Prerequisites:
- In MinIO Console (`http://localhost:9001`, user: `minio`, password: `minio123`): create a bucket named `gbfs-raw`

In Kestra UI:
1. Open `http://localhost:8080`
2. Create flow in namespace `gbfs`
3. Paste the YAML from the file above
4. Save and run (or keep schedule enabled)

This will poll every minute and push data to both MinIO and Kafka.

#### Load historical snapshots from MinIO into Postgres

Once Kestra has run a few times, load all raw snapshots from MinIO into the staging table:

```bash
docker run --rm --network gbfs-bike-monitoring_default -v "$PWD":/work -w /work python:3.11-slim \
  bash -lc "pip install sqlalchemy psycopg2-binary boto3 && python app/consumers/minio_to_postgres.py"
```

This reads every raw snapshot stored in MinIO and inserts station records into `staging.station_status_raw`.

#### Run dbt to build mart tables

```bash
docker run --rm --network gbfs-bike-monitoring_default -v "$PWD/dbt":/usr/app -w /usr/app python:3.11-slim \
  bash -lc "apt-get update -qq && apt-get install -y git -qq && pip install dbt-postgres -q && dbt run --profiles-dir profiles"
```

This materializes `staging.stg_station_status`, `marts.mart_station_latest`, and `marts.mart_bikes_over_time`.

The Streamlit dashboard at `http://localhost:8501` will now show both tiles with real data.



