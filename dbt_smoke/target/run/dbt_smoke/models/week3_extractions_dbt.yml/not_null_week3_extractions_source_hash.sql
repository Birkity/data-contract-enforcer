
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select source_hash
from "dbt_smoke"."main"."week3_extractions"
where source_hash is null



  
  
      
    ) dbt_internal_test