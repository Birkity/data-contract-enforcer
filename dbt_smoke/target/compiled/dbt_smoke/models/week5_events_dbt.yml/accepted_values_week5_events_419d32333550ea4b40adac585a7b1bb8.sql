
    
    

with all_values as (

    select
        payload_key_risks as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_key_risks

)

select *
from all_values
where value_field not in (
    'Revenue trend requires monitoring'
)


