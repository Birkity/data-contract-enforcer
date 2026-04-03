
    
    

with all_values as (

    select
        payload_regulation_set_version as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_regulation_set_version

)

select *
from all_values
where value_field not in (
    '2026-Q1'
)


