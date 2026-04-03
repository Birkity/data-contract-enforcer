
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_rule_name as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_rule_name

)

select *
from all_values
where value_field not in (
    'Bank Secrecy Act (BSA)','CRA Consideration','Jurisdiction Eligibility','Legal Entity Eligibility','OFAC Sanctions','Operating History'
)



  
  
      
    ) dbt_internal_test