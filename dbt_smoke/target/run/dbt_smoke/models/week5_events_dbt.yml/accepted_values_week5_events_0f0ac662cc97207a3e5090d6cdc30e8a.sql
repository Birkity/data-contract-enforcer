
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_document_type as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_document_type

)

select *
from all_values
where value_field not in (
    'application_proposal','balance_sheet','income_statement'
)



  
  
      
    ) dbt_internal_test