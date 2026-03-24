with ranked as (
    select
        station_id,
        bikes_available,
        docks_available,
        event_time,
        availability_bucket,
        row_number() over (
            partition by station_id
            order by event_time desc, ingested_at desc
        ) as rn
    from "gbfs_monitoring"."staging"."stg_station_status"
)

select
    station_id,
    bikes_available,
    docks_available,
    event_time,
    availability_bucket
from ranked
where rn = 1