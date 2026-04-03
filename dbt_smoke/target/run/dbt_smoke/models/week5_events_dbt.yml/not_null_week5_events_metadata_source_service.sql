
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select metadata_source_service
from "dbt_smoke"."main"."week5_events"
where metadata_source_service is null



  
  
      
    ) dbt_internal_test