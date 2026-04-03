
    
    

with all_values as (

    select
        payload_risk_level as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_risk_level

)

select *
from all_values
where value_field not in (
    'LOW','MEDIUM'
)


