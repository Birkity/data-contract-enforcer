
    
    

with all_values as (

    select
        payload_fiscal_years_loaded as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_fiscal_years_loaded

)

select *
from all_values
where value_field not in (
    '2022|2023|2024'
)


