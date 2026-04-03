
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select sequence_number
from "dbt_smoke"."main"."week5_events"
where sequence_number is null



  
  
      
    ) dbt_internal_test