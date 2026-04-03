
    
    

with all_values as (

    select
        payload_approved_amount_usd as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_approved_amount_usd

)

select *
from all_values
where value_field not in (
    '1286000.0','202000.0','2410000.0','913000.0'
)


