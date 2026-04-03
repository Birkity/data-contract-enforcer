
    
    

with all_values as (

    select
        payload_facts_page_references_net_income as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_facts_page_references_net_income

)

select *
from all_values
where value_field not in (
    'page 1, table 1, row 9'
)


