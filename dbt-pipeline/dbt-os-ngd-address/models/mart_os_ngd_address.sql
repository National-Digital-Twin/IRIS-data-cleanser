{{ config(materialized='table') }}

select *
from {{ ref('stg_os_ngd_address') }}
