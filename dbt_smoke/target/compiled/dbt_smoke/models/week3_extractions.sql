select
  doc_id,
  source_path,
  source_hash,
  entities_count,
  extraction_model,
  processing_time_ms,
  token_count_input,
  token_count_output,
  replace(cast(extracted_at as varchar), ' ', 'T') as extracted_at,
  fact_fact_id,
  fact_text,
  fact_entity_refs_count,
  fact_entity_refs,
  fact_confidence,
  fact_page_ref,
  fact_source_excerpt
from "dbt_smoke"."main"."week3_extractions_flat"