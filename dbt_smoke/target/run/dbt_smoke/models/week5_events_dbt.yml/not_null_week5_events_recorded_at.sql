
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select recorded_at
from "dbt_smoke"."main"."week5_events"
where recorded_at is null



  
  
      
    ) dbt_internal_test