select
    station_id,
    bikes_available,
    docks_available,
    event_time,
    ingested_at,
    raw_payload,
    case
        when bikes_available <= 2 then 'low'
        when bikes_available <= 7 then 'medium'
        else 'high'
    end as availability_bucket
from {{ source('staging', 'station_status_raw') }}
