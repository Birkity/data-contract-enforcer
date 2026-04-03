
    
    

with all_values as (

    select
        payload_tool_name as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_tool_name

)

select *
from all_values
where value_field not in (
    'query_applicant_registry','week3_extraction_pipeline'
)


