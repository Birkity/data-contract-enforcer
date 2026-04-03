

select *
from "dbt_smoke"."main"."week5_events"
where payload_executed_at is not null
  and not regexp_full_match(cast(payload_executed_at as varchar), '^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*')
