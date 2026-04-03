
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_loan_purpose as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_loan_purpose

)

select *
from all_values
where value_field not in (
    'acquisition','equipment_financing','expansion','real_estate','refinancing','working_capital'
)



  
  
      
    ) dbt_internal_test