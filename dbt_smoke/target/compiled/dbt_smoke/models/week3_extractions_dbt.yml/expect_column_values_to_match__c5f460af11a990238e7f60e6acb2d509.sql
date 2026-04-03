

select *
from "dbt_smoke"."main"."week3_extractions"
where fact_fact_id is not null
  and not regexp_full_match(cast(fact_fact_id as varchar), '^[0-9a-fA-F-]{36}$')
