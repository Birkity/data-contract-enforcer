
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select extracted_at
from "dbt_smoke"."main"."week3_extractions"
where extracted_at is null



  
  
      
    ) dbt_internal_test