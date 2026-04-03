
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_decline_reasons as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_decline_reasons

)

select *
from all_values
where value_field not in (
    'Compliance hard block: REG-002','Compliance hard block: REG-003','Insufficient debt service coverage|High leverage'
)



  
  
      
    ) dbt_internal_test