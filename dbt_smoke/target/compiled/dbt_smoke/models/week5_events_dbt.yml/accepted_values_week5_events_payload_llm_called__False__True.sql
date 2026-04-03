
    
    

with all_values as (

    select
        payload_llm_called as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_llm_called

)

select *
from all_values
where value_field not in (
    'False','True'
)


