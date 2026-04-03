
    
    

with all_values as (

    select
        payload_submission_channel as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_submission_channel

)

select *
from all_values
where value_field not in (
    'agent','branch','mobile','web'
)


