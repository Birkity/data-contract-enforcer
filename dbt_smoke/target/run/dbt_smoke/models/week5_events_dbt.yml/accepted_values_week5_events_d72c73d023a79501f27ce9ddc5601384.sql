
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_evaluation_notes as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_evaluation_notes

)

select *
from all_values
where value_field not in (
    'Bank Secrecy Act (BSA): Clear.','Jurisdiction Eligibility: Clear.','Legal Entity Eligibility: Clear.','OFAC Sanctions: Clear.','Operating History: Clear.'
)



  
  
      
    ) dbt_internal_test