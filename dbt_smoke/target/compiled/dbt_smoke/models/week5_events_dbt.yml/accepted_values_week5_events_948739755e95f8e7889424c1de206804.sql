
    
    

with all_values as (

    select
        payload_note_text as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_note_text

)

select *
from all_values
where value_field not in (
    'Applicant jurisdiction qualifies for CRA consideration.'
)


