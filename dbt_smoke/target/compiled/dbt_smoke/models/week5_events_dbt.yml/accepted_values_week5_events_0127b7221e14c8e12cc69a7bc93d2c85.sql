
    
    

with all_values as (

    select
        payload_inputs_validated as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_inputs_validated

)

select *
from all_values
where value_field not in (
    'application_id|company_profile|regulation_set_version','application_id|credit_stream|fraud_stream|compliance_stream','application_id|document_ids|applicant_registry_access','application_id|document_package_id|applicant_id','application_id|extracted_facts_events|registry_access'
)


