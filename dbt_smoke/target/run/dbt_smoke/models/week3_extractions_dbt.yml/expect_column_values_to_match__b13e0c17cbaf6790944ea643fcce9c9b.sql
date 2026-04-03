
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  

select *
from "dbt_smoke"."main"."week3_extractions"
where source_hash is not null
  and not regexp_full_match(cast(source_hash as varchar), '^[a-f0-9]{64}$')

  
  
      
    ) dbt_internal_test