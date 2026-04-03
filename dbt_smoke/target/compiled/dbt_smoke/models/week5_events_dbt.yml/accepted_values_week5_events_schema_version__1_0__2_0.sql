
    
    

with all_values as (

    select
        schema_version as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by schema_version

)

select *
from all_values
where value_field not in (
    '1.0','2.0'
)


