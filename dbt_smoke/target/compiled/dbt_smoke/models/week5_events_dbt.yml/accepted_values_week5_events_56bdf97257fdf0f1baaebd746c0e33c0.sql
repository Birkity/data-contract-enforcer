
    
    

with all_values as (

    select
        payload_pipeline_version as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_pipeline_version

)

select *
from all_values
where value_field not in (
    'week3-v1.0'
)


