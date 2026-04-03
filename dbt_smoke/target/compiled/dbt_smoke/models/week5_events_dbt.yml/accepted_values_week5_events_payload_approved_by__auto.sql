
    
    

with all_values as (

    select
        payload_approved_by as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_approved_by

)

select *
from all_values
where value_field not in (
    'auto'
)


