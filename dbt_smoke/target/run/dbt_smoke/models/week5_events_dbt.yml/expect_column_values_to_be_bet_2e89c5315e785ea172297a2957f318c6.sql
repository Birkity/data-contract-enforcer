
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
with validation as (
    select
        *,
        try_cast(payload_facts_field_confidence_total_assets as double) as __dbt_expectations_value
    from "dbt_smoke"."main"."week5_events"
)
select *
from validation
where payload_facts_field_confidence_total_assets is not null
  and (
    __dbt_expectations_value is null
     or __dbt_expectations_value < 0.0 
     or __dbt_expectations_value > 1.0 
  )

  
  
      
    ) dbt_internal_test