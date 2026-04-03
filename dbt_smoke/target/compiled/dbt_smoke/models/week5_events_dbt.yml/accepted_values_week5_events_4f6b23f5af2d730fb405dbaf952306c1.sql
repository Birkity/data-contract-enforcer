
    
    

with all_values as (

    select
        payload_rule_id as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_rule_id

)

select *
from all_values
where value_field not in (
    'REG-001','REG-002','REG-003','REG-004','REG-005','REG-006'
)


