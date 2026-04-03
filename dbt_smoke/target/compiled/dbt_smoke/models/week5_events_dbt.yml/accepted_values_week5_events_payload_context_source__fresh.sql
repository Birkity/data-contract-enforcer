
    
    

with all_values as (

    select
        payload_context_source as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_context_source

)

select *
from all_values
where value_field not in (
    'fresh'
)


