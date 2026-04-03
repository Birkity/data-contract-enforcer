
    
    

with all_values as (

    select
        payload_orchestrator_session_id as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_orchestrator_session_id

)

select *
from all_values
where value_field not in (
    'sess-dec-19e0d79e','sess-dec-21c739cd','sess-dec-ca7fdd98','sess-dec-cb6f3ee5','sess-dec-d320af39','sess-dec-eca00f34','sess-dec-ed8b5b06'
)


