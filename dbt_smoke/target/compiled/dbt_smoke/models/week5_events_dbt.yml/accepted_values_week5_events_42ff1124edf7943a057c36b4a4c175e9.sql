
    
    

with all_values as (

    select
        payload_facts_fiscal_year_end as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_facts_fiscal_year_end

)

select *
from all_values
where value_field not in (
    '2024-12-31'
)


