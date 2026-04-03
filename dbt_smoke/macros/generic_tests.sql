{% test expect_column_values_to_be_between(model, column_name, min_value=None, max_value=None) %}
with validation as (
    select
        *,
        try_cast({{ column_name }} as double) as __dbt_expectations_value
    from {{ model }}
)
select *
from validation
where {{ column_name }} is not null
  and (
    __dbt_expectations_value is null
    {% if min_value is not none %} or __dbt_expectations_value < {{ min_value }} {% endif %}
    {% if max_value is not none %} or __dbt_expectations_value > {{ max_value }} {% endif %}
  )
{% endtest %}

{% test expect_column_values_to_match_regex(model, column_name, regex) %}
{% set effective_regex = regex if regex.endswith('$') else regex ~ '.*' %}
select *
from {{ model }}
where {{ column_name }} is not null
  and not regexp_full_match(cast({{ column_name }} as varchar), '{{ effective_regex | replace("'", "''") }}')
{% endtest %}
