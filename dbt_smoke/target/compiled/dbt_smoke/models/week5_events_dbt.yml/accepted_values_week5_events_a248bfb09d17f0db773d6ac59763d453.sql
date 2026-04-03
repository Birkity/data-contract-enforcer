
    
    

with all_values as (

    select
        payload_failure_reason as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_failure_reason

)

select *
from all_values
where value_field not in (
    'Bank Secrecy Act (BSA) check failed.','Jurisdiction Eligibility check failed.','OFAC Sanctions check failed.'
)


