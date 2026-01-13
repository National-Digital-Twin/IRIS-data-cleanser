{{ config(materialized='table') }}

select 
    uprn as "UPRN",
    parentuprn as "ParentUPRN",
    rootuprn as "RootUPRN",
    toid as "TOID",
    fulladdress as "Address",
    postcode as "Postcode",
    easting as "Easting",
    northing as "Northing",
    latitude as "Latitude",
    longitude as "Longitude"
from {{ ref('stg_address_join_toid') }}
