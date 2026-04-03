
    
    

with all_values as (

    select
        payload_document_format as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_document_format

)

select *
from all_values
where value_field not in (
    'pdf','xlsx'
)


