
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_has_prior_loans as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_has_prior_loans

)

select *
from all_values
where value_field not in (
    'True'
)



  
  
      
    ) dbt_internal_test