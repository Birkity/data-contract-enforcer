
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select doc_id
from "dbt_smoke"."main"."week3_extractions"
where doc_id is null



  
  
      
    ) dbt_internal_test