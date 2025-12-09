{{ config(materialized='view') }}

-- Keep the latest record per UPRN (by lodgement_date desc, then inspection_date desc).
-- TODO: once ground-truth comparisons are done, consider keeping all EPC records and only dropping exact duplicates,
-- or add a separate view for "latest per UPRN" alongside a full-history view.

with ranked as (
    select
        *,
        row_number() over (
            partition by uprn
            order by lodgement_date desc, saprating desc, lmk_key desc
        ) as rn
    from {{ ref('int_epc_address_features') }}
)

select
    lmk_key,
    uprn,
    address,
    postcode,
    saprating,
    sapband,
    lodgement_date,
    construction_age_band,
    posttown,
    built_form,
    total_floor_area,
    environmental_impact_rating,
    tco2,
    heating_cost_gbp_per_yr,
    water_heating_cost_gbp_per_yr,
    lighting_cost_gbp_per_yr,
    property_type,
    main_heating_category,
    main_fuel_type,
    multiple_glazing_type,
    roof_construction,
    roof_insulation_location,
    roof_insulation_thickness,
    wall_construction,
    wall_insulation_type,
    floor_construction,
    floor_insulation,
    windows_description,
    floor_description,
    open_fireplaces_count,
    renewables,
    ventilation,
    certificate_type
from ranked
where rn = 1
