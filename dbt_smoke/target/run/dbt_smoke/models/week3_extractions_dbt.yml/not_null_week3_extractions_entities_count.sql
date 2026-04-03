
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select entities_count
from "dbt_smoke"."main"."week3_extractions"
where entities_count is null



  
  
      
    ) dbt_internal_test