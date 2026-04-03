
    
    

with all_values as (

    select
        payload_adverse_action_codes as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_adverse_action_codes

)

select *
from all_values
where value_field not in (
    'COMPLIANCE_BLOCK','HIGH_DEBT_BURDEN'
)


