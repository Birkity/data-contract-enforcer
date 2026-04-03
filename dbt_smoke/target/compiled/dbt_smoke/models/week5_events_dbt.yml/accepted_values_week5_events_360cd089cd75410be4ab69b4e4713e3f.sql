
    
    

with all_values as (

    select
        payload_auditor_notes as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_auditor_notes

)

select *
from all_values
where value_field not in (
    'Financial statements appear internally consistent. Balance sheet balances. Revenue consistent with prior year trajectory.'
)


