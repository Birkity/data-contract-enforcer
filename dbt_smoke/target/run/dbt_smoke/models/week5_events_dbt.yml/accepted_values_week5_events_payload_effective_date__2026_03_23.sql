
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_effective_date as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_effective_date

)

select *
from all_values
where value_field not in (
    '2026-03-23'
)



  
  
      
    ) dbt_internal_test