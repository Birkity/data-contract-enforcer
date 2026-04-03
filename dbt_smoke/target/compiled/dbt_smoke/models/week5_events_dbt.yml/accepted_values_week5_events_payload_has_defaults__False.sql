
    
    

with all_values as (

    select
        payload_has_defaults as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_has_defaults

)

select *
from all_values
where value_field not in (
    'False'
)


