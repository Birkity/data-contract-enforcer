
with validation as (
    select
        *,
        try_cast(payload_overall_confidence as double) as __dbt_expectations_value
    from "dbt_smoke"."main"."week5_events"
)
select *
from validation
where payload_overall_confidence is not null
  and (
    __dbt_expectations_value is null
     or __dbt_expectations_value < 0.0 
     or __dbt_expectations_value > 1.0 
  )
