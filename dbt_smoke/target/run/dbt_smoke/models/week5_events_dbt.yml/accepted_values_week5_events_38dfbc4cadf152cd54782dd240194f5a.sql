
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_revenue_trajectory as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_revenue_trajectory

)

select *
from all_values
where value_field not in (
    'DECLINING','GROWTH','RECOVERING','STABLE','VOLATILE'
)



  
  
      
    ) dbt_internal_test