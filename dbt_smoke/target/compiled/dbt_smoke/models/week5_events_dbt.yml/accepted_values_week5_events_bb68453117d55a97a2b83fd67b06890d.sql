
    
    

with all_values as (

    select
        aggregate_type as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by aggregate_type

)

select *
from all_values
where value_field not in (
    'AgentSession','ComplianceCheck','CreditAnalysis','DocumentPackage','FraudScreening','Loan'
)


