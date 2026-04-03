
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select extraction_model
from "dbt_smoke"."main"."week3_extractions"
where extraction_model is null



  
  
      
    ) dbt_internal_test