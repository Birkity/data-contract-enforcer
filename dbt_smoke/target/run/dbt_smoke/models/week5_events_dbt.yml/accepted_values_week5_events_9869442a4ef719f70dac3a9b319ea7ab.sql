
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_facts_page_references_total_revenue as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_facts_page_references_total_revenue

)

select *
from all_values
where value_field not in (
    'page 1, table 1, row 1'
)



  
  
      
    ) dbt_internal_test