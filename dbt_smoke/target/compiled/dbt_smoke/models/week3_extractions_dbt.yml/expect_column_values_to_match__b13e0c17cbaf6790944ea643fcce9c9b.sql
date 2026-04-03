

select *
from "dbt_smoke"."main"."week3_extractions"
where source_hash is not null
  and not regexp_full_match(cast(source_hash as varchar), '^[a-f0-9]{64}$')
