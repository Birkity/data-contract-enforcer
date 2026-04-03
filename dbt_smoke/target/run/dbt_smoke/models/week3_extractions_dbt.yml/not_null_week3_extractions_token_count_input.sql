
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select token_count_input
from "dbt_smoke"."main"."week3_extractions"
where token_count_input is null



  
  
      
    ) dbt_internal_test