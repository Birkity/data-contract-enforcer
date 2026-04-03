
    
    

with all_values as (

    select
        payload_file_hash as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_file_hash

)

select *
from all_values
where value_field not in (
    '3a3a2439911766f6','8eb66e9cbdaaa5ba','a86210f5fdceb84f','d794b166001141a2'
)


