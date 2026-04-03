

select *
from "dbt_smoke"."main"."week5_events"
where event_id is not null
  and not regexp_full_match(cast(event_id as varchar), '^[0-9a-fA-F-]{36}$')
