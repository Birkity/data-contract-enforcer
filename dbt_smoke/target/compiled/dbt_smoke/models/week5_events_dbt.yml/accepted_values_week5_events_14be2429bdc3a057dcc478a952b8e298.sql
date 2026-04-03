
    
    

with all_values as (

    select
        payload_extraction_model as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_extraction_model

)

select *
from all_values
where value_field not in (
    'mineru-1.0'
)


