
    
    

with all_values as (

    select
        payload_quality_flags_present as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_quality_flags_present

)

select *
from all_values
where value_field not in (
    'False'
)


