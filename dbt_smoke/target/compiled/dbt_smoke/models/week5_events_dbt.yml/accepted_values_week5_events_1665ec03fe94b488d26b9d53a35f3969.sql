
    
    

with all_values as (

    select
        payload_decision_risk_tier as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_decision_risk_tier

)

select *
from all_values
where value_field not in (
    'HIGH','LOW','MEDIUM'
)


