
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_next_agent_triggered as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_next_agent_triggered

)

select *
from all_values
where value_field not in (
    'compliance','credit_analysis','decision_orchestrator','fraud_detection'
)



  
  
      
    ) dbt_internal_test