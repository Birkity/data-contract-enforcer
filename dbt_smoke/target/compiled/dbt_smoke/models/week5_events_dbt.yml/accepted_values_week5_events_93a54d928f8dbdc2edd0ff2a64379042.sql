
    
    

with all_values as (

    select
        metadata_source_service as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by metadata_source_service

)

select *
from all_values
where value_field not in (
    'agentic-governance-ledger'
)


