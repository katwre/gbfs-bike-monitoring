import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine


def get_engine():
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    dbname = os.getenv("POSTGRES_DB", "gbfs_monitoring")
    user = os.getenv("POSTGRES_USER", "gbfs")
    password = os.getenv("POSTGRES_PASSWORD", "gbfs")
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}")


def read_table(query: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.begin() as connection:
        return pd.read_sql_query(query, connection)


st.set_page_config(page_title="GBFS Bike Monitoring", layout="wide")

st.title("GBFS Bike Monitoring")
st.caption("Two-tile dashboard backed by Postgres marts built from GBFS bike station status events in Bergen, Norway.")

try:
    latest_df = read_table(
        """
        select station_id, bikes_available, docks_available, event_time, availability_bucket
        from marts.mart_station_latest
        order by station_id
        """
    )
    trend_df = read_table(
        """
        select event_minute, avg_bikes_available, total_bikes_available, records_count
        from marts.mart_bikes_over_time
        order by event_minute
        """
    )
except Exception as exc:
    st.warning(
        "Dashboard marts are not available yet. Run your dbt models first, then refresh this page."
    )
    st.code(
        "docker run --rm --network gbfs-bike-monitoring_default -v \"$PWD/dbt\":/usr/app -w /usr/app ghcr.io/dbt-labs/dbt-postgres:1.10.0 run --profiles-dir profiles",
        language="bash",
    )
    st.exception(exc)
    st.stop()


col1, col2 = st.columns(2)

with col1:
    st.subheader("Stations by availability category")
    bucket_counts = (
        latest_df.groupby("availability_bucket", as_index=False)
        .size()
        .rename(columns={"size": "stations_count"})
    )
    fig_bucket = px.bar(
        bucket_counts,
        x="availability_bucket",
        y="stations_count",
        color="availability_bucket",
        category_orders={"availability_bucket": ["low", "medium", "high"]},
        title="Current station distribution",
    )
    fig_bucket.update_layout(showlegend=False)
    st.plotly_chart(fig_bucket, use_container_width=True)
    st.dataframe(latest_df.head(10), use_container_width=True)

with col2:
    st.subheader("Average bikes available over time")
    fig_trend = px.line(
        trend_df,
        x="event_minute",
        y="avg_bikes_available",
        markers=True,
        title="Average bikes available by minute",
    )
    st.plotly_chart(fig_trend, use_container_width=True)
    st.dataframe(trend_df.tail(10), use_container_width=True)
