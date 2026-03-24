
  
    

  create  table "gbfs_monitoring"."marts"."mart_bikes_over_time__dbt_tmp"
  
  
    as
  
  (
    select
    date_trunc('minute', event_time) as event_minute,
    avg(bikes_available)::numeric(10,2) as avg_bikes_available,
    sum(bikes_available) as total_bikes_available,
    count(*) as records_count
from "gbfs_monitoring"."staging"."stg_station_status"
group by 1
order by 1
  );
  