

select *
from "dbt_smoke"."main"."week3_extractions"
where extracted_at is not null
  and not regexp_full_match(cast(extracted_at as varchar), '^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*')
