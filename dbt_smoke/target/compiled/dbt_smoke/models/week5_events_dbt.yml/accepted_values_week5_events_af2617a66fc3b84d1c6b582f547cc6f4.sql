
    
    

with all_values as (

    select
        payload_executive_summary as value_field,
        count(*) as n_records

    from "dbt_smoke"."main"."week5_events"
    group by payload_executive_summary

)

select *
from all_values
where value_field not in (
    'Approval recommended. DECLINING trajectory. Compliance clear. Fraud screening low risk.','Approval recommended. GROWTH trajectory. Compliance clear. Fraud screening low risk.','Approval recommended. RECOVERING trajectory. Compliance clear. Fraud screening low risk.','Decline recommended. DECLINING trajectory. Compliance clear. Fraud screening low risk.','Decline recommended. RECOVERING trajectory. Compliance clear. Fraud screening low risk.','Human review recommended. GROWTH trajectory. Compliance clear. Fraud screening low risk.'
)


