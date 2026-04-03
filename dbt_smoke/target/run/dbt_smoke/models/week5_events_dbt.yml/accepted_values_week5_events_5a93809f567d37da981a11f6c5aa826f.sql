
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        payload_note_type as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_note_type

)

select *
from all_values
where value_field not in (
    'CRA_CONSIDERATION'
)



  
  
      
    ) dbt_internal_test