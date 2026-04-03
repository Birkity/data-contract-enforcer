
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  

select *
from "dbt_smoke"."main"."week5_events"
where occurred_at is not null
  and not regexp_full_match(cast(occurred_at as varchar), '^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*')

  
  
      
    ) dbt_internal_test