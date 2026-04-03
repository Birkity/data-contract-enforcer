
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select schema_version
from "dbt_smoke"."main"."week5_events"
where schema_version is null



  
  
      
    ) dbt_internal_test