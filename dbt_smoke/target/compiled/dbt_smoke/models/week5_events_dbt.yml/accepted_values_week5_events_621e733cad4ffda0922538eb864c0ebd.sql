
    
    

with all_values as (

    select
        payload_model_version as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_model_version

)

select *
from all_values
where value_field not in (
    'claude-sonnet-4-20250514'
)


