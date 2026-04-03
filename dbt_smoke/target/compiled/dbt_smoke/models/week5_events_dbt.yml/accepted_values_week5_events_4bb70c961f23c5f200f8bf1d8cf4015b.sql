
    
    

with all_values as (

    select
        payload_agent_type as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_agent_type

)

select *
from all_values
where value_field not in (
    'compliance','credit_analysis','decision_orchestrator','document_processing','fraud_detection'
)


