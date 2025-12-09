{{ config(materialized='view') }}

-- Map raw split fields into normalized feature columns.

select
    lmk_key,
    uprn,
    address,
    postcode,
    current_energy_efficiency as saprating,
    current_energy_rating as sapband,
    lodgement_date,
    trim(regexp_replace(construction_age_band, '^\s*England and Wales:\s*', '', 'i')) as construction_age_band,
    nullif(regexp_replace(initcap(built_form), '[^A-Za-z0-9]', '', 'g'), '') as built_form,
    total_floor_area,
    environment_impact_current as environmental_impact_rating,
    co2_emissions_current as tco2,
    heating_cost_current as heating_cost_gbp_per_yr,
    hot_water_cost_current as water_heating_cost_gbp_per_yr,
    lighting_cost_current as lighting_cost_gbp_per_yr,
    property_type,
    posttown,
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
    -- heating category (aligned with original Python mapping)
    case
        when lower(mainheat_description) like '%boiler and radiators, mains gas%' then 'BoilerRadiatorsMainsGas'
        when lower(mainheat_description) like '%electric storage heaters%' or lower(mainheat_description) like '%portable electric heaters%' then 'ElectricHeaters'
        when lower(mainheat_description) like '%boiler and radiators, lpg%' or lower(mainheat_description) like '%boiler and underfloor heating, lpg%' then 'BoilerRadiatorsLPG'
        when lower(mainheat_description) like '%boiler and radiators, oil%' or lower(mainheat_description) like '%boiler and underfloor heating, oil%' then 'BoilerRadiatorsOil'
        when lower(mainheat_description) like '%electric underfloor heating%' then 'ElectricUnderfloor'
        when lower(mainheat_description) like '%community scheme%' then 'CommunityScheme'
        when lower(mainheat_description) like '%warm air, mains gas%' then 'WarmAirMainsGas'
        when lower(mainheat_description) like '%boiler & underfloor, mains gas%' or lower(mainheat_description) like '%boiler and underfloor heating, mains gas%' then 'BoilerUnderfloorMainsGas'
        when lower(mainheat_description) like '%air source heat pump%' then 'AirSourceHeatPump'
        when lower(mainheat_description) like '%boiler and radiators, electric%' or lower(mainheat_description) like '%boiler and underfloor heating, electric%' then 'BoilerRadiatorsElectric'
        when lower(mainheat_description) like '%ground source heat pump%' then 'GroundSourceHeatPump'
        when lower(mainheat_description) like '%boiler and radiators, dual fuel%' then 'BoilerRadiatorsDualFuel'
        when lower(mainheat_description) like '%boiler and radiators, wood%' then 'BoilerRadiatorsWood'
        when lower(mainheat_description) like '%room heaters, mains gas%' then 'RoomHeatersMainsGas'
        when lower(mainheat_description) like '%no system present%' then 'NoSystemPresent'
        when lower(mainheat_description) like '%water source heat pump%' then 'WaterSourceHeatPump'
        else 'Other'
    end as main_heating_category,
    -- fuel category (aligned with original Python mapping)
    case
        when main_fuel ilike '%mains gas%' then 'MainsGas'
        when main_fuel ilike '%electricity%' or main_fuel ilike '%electric%' then 'Electricity'
        when main_fuel ilike '%oil%' then 'Oil'
        when main_fuel ilike '%lpg%' then 'LPG'
        when main_fuel ilike '%no heating/hot-water system%' then 'NoSystem'
        when main_fuel ilike '%dual fuel%' then 'DualFuel'
        when main_fuel ilike '%wood logs%' then 'WoodLogs'
        when main_fuel ilike '%wood pellets%' then 'WoodPellets'
        when main_fuel ilike '%wood chips%' then 'WoodChips'
        when main_fuel ilike '%house coal%' then 'Coal'
        when main_fuel ilike '%anthracite%' then 'Anthracite'
        when main_fuel ilike '%smokeless coal%' then 'SmokelessCoal'
        when main_fuel ilike '%biomass%' then 'Biomass'
        when main_fuel ilike '%biogas%' then 'Biogas'
        when main_fuel ilike '%invalid%' then 'Invalid'
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
    -- roof mappings
    case
        when roof_construction_raw ilike '%pitched%' then 'Pitched'
        when roof_construction_raw ilike '%roof room%' then 'RoofRoom'
        when roof_construction_raw ilike '%flat%' then 'Flat'
        when roof_construction_raw ilike '%other premises above%' then 'OtherPremisesAbove'
        when roof_construction_raw ilike '%another dwelling above%' then 'AnotherDwellingAbove'
        when roof_construction_raw ilike '%thatched%' then 'Thatched'
        else null
    end as roof_construction,
    case
        when roof_insulation_raw ilike '%mm%' then regexp_replace(roof_insulation_raw, '[^0-9]', '', 'g') || 'mm'
        else null
    end as roof_insulation_thickness,
    case
        when roof_insulation_raw is null or trim(roof_insulation_raw) = '' then null
        when roof_insulation_raw ilike '%rafters%' then 'InsulatedAtRafters'
        when roof_insulation_raw ilike '%ceiling insulated%' then 'CeilingInsulated'
        when roof_insulation_raw ilike '%flat roof%' then 'FlatRoofInsulation'
        when roof_insulation_raw ilike '%with additional insulation%' then 'ThatchedWithAdditionalInsulation'
        when roof_insulation_raw ilike '%thatched%' then 'InsulatedWithThatched'
        when roof_insulation_raw ilike '%limited insulation%' and roof_insulation_raw ilike '%assumed%' then 'LimitedInsulationAssumed'
        when roof_insulation_raw ilike '%limited insulation%' then 'LimitedInsulation'
        when roof_insulation_raw ilike '%insulated%' and roof_insulation_raw ilike '%assumed%' then 'InsulatedAssumed'
        when roof_insulation_raw ilike '%insulated%' then 'Insulated'
        when roof_insulation_raw ilike '%loft insulation%' and roof_insulation_raw ilike '%assumed%' then 'LoftInsulationAssumed'
        when roof_insulation_raw ilike '%loft insulation%' then 'LoftInsulation'
        when roof_insulation_raw ilike '%no insulation%' and roof_insulation_raw ilike '%assumed%' then 'NoInsulationAssumedInRoof'
        when roof_insulation_raw ilike '%no insulation%' then 'NoInsulationInRoof'
        when roof_insulation_raw ilike '%unknown%' then null
        else nullif(trim(roof_insulation_extra), '')
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
from {{ ref('int_epc_address_split') }}
