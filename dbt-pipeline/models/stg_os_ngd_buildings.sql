{{ config(materialized = 'table') }}

(
SELECT
*
FROM {{ source('postgres', 'os_ngd_buildings_mini') }}
)
