
    
    

with all_values as (

    select
        payload_recommendation as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_recommendation

)

select *
from all_values
where value_field not in (
    'APPROVE','DECLINE','PROCEED','REFER'
)


