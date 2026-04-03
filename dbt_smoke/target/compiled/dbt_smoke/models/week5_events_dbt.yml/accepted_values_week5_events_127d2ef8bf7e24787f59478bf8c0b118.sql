
    
    

with all_values as (

    select
        payload_langgraph_graph_version as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_langgraph_graph_version

)

select *
from all_values
where value_field not in (
    '1.0.0-sim'
)


