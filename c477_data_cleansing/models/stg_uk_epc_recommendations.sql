{{ config (materialized = 'table') }}

(
    SELECT
        CAST(NULL AS TEXT) AS building_reference_number,
        CAST(NULL AS TEXT) AS lmk_key,
        "CERTIFICATE_NUMBER" AS certificate_number,
        CAST(NULL AS BIGINT) AS improvement_item,
        "IMPROVEMENT_DESCR_TEXT" AS improvement_descr_text,
        CAST(NULL AS TEXT) AS improvement_summary_text,
        CAST(NULL AS BIGINT) AS improvement_id,
        CAST(NULL AS TEXT) AS improvement_id_text,
        "ENERGY_RATING_AFTER_IMPROVEMENT" AS energy_rating_after_improvement,
        CAST(NULL AS TEXT) AS environmental_rating_after_improvement,
        CAST(NULL AS TEXT) AS payback_type,
        CAST(NULL AS TEXT) AS co2_impact,
        CAST(NULL AS TEXT) AS code,
        "INDICATIVE_COST" AS indicative_cost,
        "TYPICAL_SAVINGS" AS typical_savings,
        CAST(NULL AS TEXT) AS green_deal_eligible,
        'domestic' AS recommendation_type
    FROM {{ source('postgres', 'northern_ireland_recommendations') }}
)

UNION

(
    SELECT
        "BUILDING_REFERENCE_NUMBER" AS building_reference_number,
        CAST(NULL AS TEXT) AS lmk_key,
        CAST(NULL AS TEXT) AS certificate_number,
        CAST(NULL AS BIGINT) AS improvement_item,
        "IMPROVEMENT_DESCR_TEXT" AS improvement_descr_text,
        CAST(NULL AS TEXT) AS improvement_summary_text,
        CAST(NULL AS BIGINT) AS improvement_id,
        CAST(NULL AS TEXT) AS improvement_id_text,
        "ENERGY_RATING_AFTER_IMPROVEMENT" AS energy_rating_after_improvement,
        "ENVIRONMENTAL_RATING_AFTER_IMPROVEMENT" AS environmental_rating_after_improvement,
        CAST(NULL AS TEXT) AS payback_type,
        CAST(NULL AS TEXT) AS co2_impact,
        CAST(NULL AS TEXT) AS code,
        "INDICATIVE_COST" AS indicative_cost,
        "TYPICAL_SAVING" AS typical_savings,
        "GREEN_DEAL_ELIGIBLE" AS green_deal_eligible,
        'domestic' AS recommendation_type
    FROM {{ source('postgres', 'scotland_domestic_recommendations') }}
)

UNION

(
    SELECT
        "BUILDING_REFERENCE_NUMBER" AS building_reference_number,
        CAST(NULL AS TEXT) AS lmk_key,
        CAST(NULL AS TEXT) AS certificate_number,
        CAST(NULL AS BIGINT) AS improvement_item,
        "IMPROVEMENT_DESCR_TEXT" AS improvement_descr_text,
        CAST(NULL AS TEXT) AS improvement_summary_text,
        CAST(NULL AS BIGINT) AS improvement_id,
        CAST(NULL AS TEXT) AS improvement_id_text,
        CAST(NULL AS TEXT) AS energy_rating_after_improvement,
        CAST(NULL AS TEXT) AS environmental_rating_after_improvement,
        "CODE" AS code,
        "C02_IMPACT" AS co2_impact,
        "PAYBACK_TYPE" AS payback_type,
        CAST(NULL AS TEXT) AS green_deal_eligible,
        CAST(NULL AS TEXT) AS indicative_cost,
        CAST(NULL AS TEXT) AS typical_savings,
        'nondomestic' AS recommendation_type
    FROM {{ source('postgres', 'scotland_nondomestic_recommendations') }}
)

UNION

(
    SELECT
        CAST(NULL AS TEXT) AS building_reference_number,
        "LMK_KEY" AS lmk_key,
        CAST(NULL AS TEXT) AS certificate_number,
        "IMPROVEMENT_ITEM" AS improvement_item,
        "IMPROVEMENT_SUMMARY_TEXT" AS improvement_summary_text,
        "IMPROVEMENT_DESCR_TEXT" AS improvement_descr_text,
        CAST("IMPROVEMENT_ID" AS BIGINT) AS improvement_id,
        CAST("IMPROVEMENT_ID_TEXT" AS TEXT) AS improvement_id_text,
        CAST(NULL AS TEXT) AS energy_rating_after_improvement,
        CAST(NULL AS TEXT) AS environmental_rating_after_improvement,
        CAST(NULL AS TEXT) AS code,
        CAST(NULL AS TEXT) AS co2_impact,
        CAST(NULL AS TEXT) AS payback_type,
        CAST(NULL AS TEXT) AS green_deal_eligible,
        "INDICATIVE_COST" AS indicative_cost,
        CAST(NULL AS TEXT) AS typical_savings,
        'domestic' AS recommendation_type
    FROM {{ source('postgres', 'eng_wales_domestic_recommendations') }}
)

UNION

(
    SELECT
        CAST(NULL AS TEXT) AS building_reference_number,
        "LMK_KEY" AS lmk_key,
        CAST(NULL AS TEXT) AS certificate_number,
        CAST("RECOMMENDATION_ITEM" AS BIGINT) AS improvement_item,
        CAST(NULL AS TEXT) AS improvement_summary_text,
        "RECOMMENDATION" AS improvement_descr_text,
        CAST(NULL AS BIGINT) AS improvement_id,
        CAST(NULL AS TEXT) AS improvement_id_text,
        CAST(NULL AS TEXT) AS energy_rating_after_improvement,
        CAST(NULL AS TEXT) AS environmental_rating_after_improvement,
        "RECOMMENDATION_CODE" AS code,
        CAST(NULL AS TEXT) AS co2_impact,
        CAST(NULL AS TEXT) AS payback_type,
        CAST(NULL AS TEXT) AS green_deal_eligible,
        CAST(NULL AS TEXT) AS indicative_cost,
        CAST(NULL AS TEXT) AS typical_savings,
        'nondomestic' AS recommendation_type
    FROM {{ source('postgres', 'eng_wales_nondomestic_recommendations') }}
)
