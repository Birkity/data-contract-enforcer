
    
    

with all_values as (

    select
        payload_agent_id as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_agent_id

)

select *
from all_values
where value_field not in (
    'compliance-agent-1','credit-agent-1','doc-agent-1','fraud-agent-1','orchestrator-1'
)


