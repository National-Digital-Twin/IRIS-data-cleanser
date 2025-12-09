{{ config(materialized='view') }}

-- Derive feature-ready fields from the cleaned EPC slice.

with base as (
    select
        lmk_key,
        uprn,
        address,
        postcode,
        property_type,
        built_form,
        current_energy_rating,
        current_energy_efficiency,
        roof_description,
        walls_description,
        floor_description,
        windows_description,
        glazed_type,
        total_floor_area,
        environment_impact_current,
        lodgement_date,
        co2_emissions_current,
        floor_level,
        heating_cost_current,
        construction_age_band,
        main_heating_controls,
        mainheat_description,
        main_fuel,
        number_open_fireplaces,
        wind_turbine_count,
        mechanical_ventilation,
        hot_water_cost_current,
        lighting_cost_current,
        inspection_date,
        flat_storey_count,
        certificate_type
    from {{ ref('int_epc_address_clean') }}
),

split_descriptions as (
    select
        b.*,
        regexp_split_to_array(coalesce(b.roof_description, ''), ',') as roof_parts,
        regexp_split_to_array(coalesce(b.walls_description, ''), ',') as wall_parts,
        regexp_split_to_array(coalesce(b.floor_description, ''), ',') as floor_parts
    from base b
),

feature_map as (
    select
        lmk_key,
        uprn,
        address,
        postcode,
        property_type,
        -- normalize built form to PascalCase-ish
        regexp_replace(initcap(coalesce(built_form, '')), '[^A-Za-z0-9]', '', 'g') as built_form_norm,
        current_energy_rating as sapband,
        current_energy_efficiency as saprating,
        -- roof splits
        trim(roof_parts[1]) as roof_construction_raw,
        trim(roof_parts[2]) as roof_insulation_raw,
        trim(roof_parts[3]) as roof_insulation_extra,
        -- wall splits
        trim(wall_parts[1]) as wall_construction_raw,
        trim(wall_parts[2]) as wall_insulation_raw,
        trim(wall_parts[3]) as wall_insulation_thickness_raw,
        -- floor splits
        trim(floor_parts[1]) as floor_construction_raw,
        trim(floor_parts[2]) as floor_insulation_raw,
        trim(floor_parts[3]) as floor_insulation_thickness_raw,
        windows_description,
        floor_description,
        glazed_type,
        total_floor_area,
        environment_impact_current,
        lodgement_date,
        co2_emissions_current,
        floor_level,
        heating_cost_current,
        construction_age_band,
        main_heating_controls,
        mainheat_description,
        main_fuel,
        number_open_fireplaces,
        wind_turbine_count,
        mechanical_ventilation,
        hot_water_cost_current,
        lighting_cost_current,
        inspection_date,
        flat_storey_count,
        certificate_type
    from split_descriptions
),

mapped as (
    select
        lmk_key,
        uprn,
        address,
        postcode,
        saprating,
        sapband,
        lodgement_date,
        construction_age_band,
        built_form_norm as built_form,
        total_floor_area,
        environment_impact_current as environmental_impact_rating,
        co2_emissions_current as tco2,
        heating_cost_current as heating_cost_gbp_per_yr,
        hot_water_cost_current as water_heating_cost_gbp_per_yr,
        lighting_cost_current as lighting_cost_gbp_per_yr,
        property_type,
        flat_storey_count as storeys_count,
        -- map flat level to numeric
        case
            when lower(floor_level) in ('basement', '-1', '-1.0') then -1
            when lower(floor_level) in ('ground', 'ground floor', '00', '0', '0.0') then 0
            when lower(floor_level) in ('1st', '01', '1', '1.0') then 1
            when lower(floor_level) in ('2nd', '02', '2', '2.0') then 2
            when lower(floor_level) in ('3rd', '03', '3', '3.0') then 3
            when lower(floor_level) in ('4th', '04', '4', '4.0') then 4
            when lower(floor_level) in ('5th', '05', '5', '5.0') then 5
            when lower(floor_level) = '6th' then 6
            when lower(floor_level) = '7th' or floor_level = '07' then 7
            when lower(floor_level) = '8th' then 8
            when lower(floor_level) = '12th' then 12
            when lower(floor_level) = 'topfloor' then 13
            when lower(floor_level) = 'midfloor' then 6
            else null
        end as flat_level,
        -- heating category (simplified mappings)
        case
            when mainheat_description ilike '%mains gas%' and mainheat_description ilike '%boiler%' then 'BoilerRadiatorsMainsGas'
            when mainheat_description ilike '%electric storage heaters%' then 'ElectricHeaters'
            when mainheat_description ilike '%lpg%' then 'BoilerRadiatorsLPG'
            when mainheat_description ilike '%oil%' then 'BoilerRadiatorsOil'
            when mainheat_description ilike '%air source heat pump%' then 'AirSourceHeatPump'
            when mainheat_description ilike '%ground source heat pump%' then 'GroundSourceHeatPump'
            when mainheat_description ilike '%water source heat pump%' then 'WaterSourceHeatPump'
            when mainheat_description ilike '%community scheme%' then 'CommunityScheme'
            when mainheat_description ilike '%electric underfloor%' then 'ElectricUnderfloor'
            when mainheat_description ilike '%warm air%' and mainheat_description ilike '%mains gas%' then 'WarmAirMainsGas'
            when mainheat_description ilike '%no system%' then 'NoSystemPresent'
            else 'Other'
        end as main_heating_category,
        -- fuel category
        case
            when main_fuel ilike '%mains gas%' then 'MainsGas'
            when main_fuel ilike '%electric%' then 'Electricity'
            when main_fuel ilike '%oil%' then 'Oil'
            when main_fuel ilike '%lpg%' then 'LPG'
            when main_fuel ilike '%dual fuel%' then 'DualFuel'
            when main_fuel ilike '%wood%' then 'Wood'
            when main_fuel ilike '%coal%' then 'Coal'
            when main_fuel ilike '%biomass%' then 'Biomass'
            else 'Other'
        end as main_fuel_type,
        main_heating_controls as main_heating_control,
        -- glazing
        case
            when glazed_type ilike '%double%' and glazed_type ilike '%2002%' then 'DoubleGlazingAfter2002'
            when glazed_type ilike '%double%' then 'DoubleGlazing'
            when glazed_type ilike '%triple%' then 'TripleGlazing'
            when glazed_type ilike '%secondary%' then 'SecondaryGlazing'
            when glazed_type ilike '%single%' then 'SingleGlazing'
            else null
        end as multiple_glazing_type,
        -- roof mappings (aligned to original Python transform_roof_construction)
        case
            when roof_construction_raw ilike '%pitched%' then 'Pitched'
            when roof_construction_raw ilike '%roof room%' then 'RoofRoom'
            when roof_construction_raw ilike '%flat%' then 'Flat'
            when roof_construction_raw ilike '%other premises above%' then 'OtherPremisesAbove'
            when roof_construction_raw ilike '%another dwelling above%' then 'AnotherDwellingAbove'
            when roof_construction_raw ilike '%thatched%' then 'Thatched'
            else null
        end as roof_construction,
        -- extract thickness if roof_insulation_raw contains 'mm'
        case
            when roof_insulation_raw ilike '%mm%' then regexp_replace(roof_insulation_raw, '[^0-9]', '', 'g') || 'mm'
            else null
        end as roof_insulation_thickness,
        case
            when roof_insulation_raw ilike '%loft%' then 'LoftInsulation'
            when roof_insulation_raw ilike '%insulated%' then 'Insulated'
            else nullif(trim(roof_insulation_raw), '')
        end as roof_insulation_location,
        -- wall mappings
        case
            when wall_construction_raw ilike '%cavity%' then 'CavityWall'
            when wall_construction_raw ilike '%timber%' then 'TimberFrame'
            when wall_construction_raw ilike '%solid brick%' then 'SolidBrick'
            when wall_construction_raw ilike '%sandstone%' then 'Sandstone'
            when wall_construction_raw ilike '%granite%' or wall_construction_raw ilike '%whin%' then 'GraniteOrWhinstone'
            else coalesce(nullif(trim(wall_construction_raw), ''), 'Other')
        end as wall_construction,
        case
            when wall_insulation_raw ilike '%filled cavity%' and wall_insulation_raw ilike '%internal%' then 'FilledCavityAndInternalInsulation'
            when wall_insulation_raw ilike '%filled cavity%' and wall_insulation_raw ilike '%external%' then 'FilledCavityAndExternalInsulation'
            when wall_insulation_raw ilike '%filled cavity%' then 'FilledCavity'
            when wall_insulation_raw ilike '%internal%' then 'WithInternalInsulation'
            when wall_insulation_raw ilike '%external%' then 'WithExternalInsulation'
            when wall_insulation_raw ilike '%additional insulation%' then 'WithAdditionalInsulation'
            else null
        end as wall_insulation_type,
        wall_insulation_thickness_raw as wall_insulation_thickness,
        -- floor mappings
        case
            when floor_construction_raw ilike '%solid%' then 'Solid'
            when floor_construction_raw ilike '%suspended%' then 'Suspended'
            when floor_construction_raw ilike '%other premises below%' then 'OtherPremisesBelow'
            when floor_construction_raw ilike '%another dwelling below%' then 'AnotherDwellingBelow'
            else null
        end as floor_construction,
        case
            when floor_insulation_raw ilike '%uninsulated%' then 'NoInsulation'
            when floor_insulation_raw ilike '%assumed%' then trim(replace(floor_insulation_raw, '(assumed)', ''))
            else nullif(trim(floor_insulation_raw), '')
        end as floor_insulation,
        nullif(trim(floor_insulation_thickness_raw), '') as floor_insulation_thickness,
        windows_description,
        floor_description,
        number_open_fireplaces as open_fireplaces_count,
        wind_turbine_count as renewables,
        mechanical_ventilation as ventilation,
        certificate_type
    from feature_map
)

select *
from mapped
