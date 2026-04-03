
    
    

with all_values as (

    select
        payload_facts_balance_sheet_balances as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_facts_balance_sheet_balances

)

select *
from all_values
where value_field not in (
    'True'
)


