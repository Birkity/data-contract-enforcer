
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select aggregate_id
from "dbt_smoke"."main"."week5_events"
where aggregate_id is null



  
  
      
    ) dbt_internal_test