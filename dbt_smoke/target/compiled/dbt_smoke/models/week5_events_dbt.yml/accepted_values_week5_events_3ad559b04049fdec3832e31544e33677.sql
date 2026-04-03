
    
    

with all_values as (

    select
        payload_required_document_types as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_required_document_types

)

select *
from all_values
where value_field not in (
    'application_proposal|income_statement|balance_sheet'
)


