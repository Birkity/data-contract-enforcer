
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  

select *
from "dbt_smoke"."main"."week3_extractions"
where doc_id is not null
  and not regexp_full_match(cast(doc_id as varchar), '^[0-9a-fA-F-]{36}$')

  
  
      
    ) dbt_internal_test