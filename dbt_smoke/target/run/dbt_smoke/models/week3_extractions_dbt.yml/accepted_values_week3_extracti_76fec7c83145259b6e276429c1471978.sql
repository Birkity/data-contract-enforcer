
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        extraction_model as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week3_extractions"
    group by extraction_model

)

select *
from all_values
where value_field not in (
    'layout_aware','layout_aware+llm_assisted','layout_aware+llm_assisted+regex','layout_aware+regex','layout_aware+table_parse','ocr_heavy','ocr_heavy+llm_assisted+regex'
)



  
  
      
    ) dbt_internal_test