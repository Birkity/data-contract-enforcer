
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select processing_time_ms
from "dbt_smoke"."main"."week3_extractions"
where processing_time_ms is null



  
  
      
    ) dbt_internal_test