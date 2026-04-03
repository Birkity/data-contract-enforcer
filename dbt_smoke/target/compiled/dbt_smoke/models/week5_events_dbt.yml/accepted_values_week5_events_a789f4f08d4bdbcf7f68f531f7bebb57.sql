
    
    

with all_values as (

    select
        payload_all_analyses_complete as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_all_analyses_complete

)

select *
from all_values
where value_field not in (
    'True'
)


