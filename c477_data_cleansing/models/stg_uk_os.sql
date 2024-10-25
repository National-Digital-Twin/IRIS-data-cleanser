{{ config(materialized='table') }}

(SELECT * FROM {{ ref("stg_os_aberdeen") }})
-- ORDER BY "postcode" ASC)
UNION
(SELECT * FROM {{ ref("stg_os_aberdeenshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_angus") }})
UNION
(SELECT * FROM {{ ref("stg_os_argyll_and_bute") }})
UNION
(SELECT * FROM {{ ref("stg_os_clackmannanshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_county_antrim") }})
UNION
(SELECT * FROM {{ ref("stg_os_county_armagh") }})
UNION
(SELECT * FROM {{ ref("stg_os_county_down") }})
UNION
(SELECT * FROM {{ ref("stg_os_county_fermanagh") }})
UNION
(SELECT * FROM {{ ref("stg_os_county_londonderry") }})
UNION
(SELECT * FROM {{ ref("stg_os_county_tyrone") }})
UNION
(SELECT * FROM {{ ref("stg_os_dumfries_and_galloway") }})
UNION
(SELECT * FROM {{ ref("stg_os_dundee") }})
UNION
(SELECT * FROM {{ ref("stg_os_east_ayrshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_east_dunbartonshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_east_lothian") }})
UNION
(SELECT * FROM {{ ref("stg_os_east_renfrewshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_edinburgh") }})
UNION
(SELECT * FROM {{ ref("stg_os_falkirk") }})
UNION
(SELECT * FROM {{ ref("stg_os_fife") }})
UNION
(SELECT * FROM {{ ref("stg_os_glasgow") }})
UNION
(SELECT * FROM {{ ref("stg_os_highland") }})
UNION
(SELECT * FROM {{ ref("stg_os_inverclyde") }})
UNION
(SELECT * FROM {{ ref("stg_os_midlothian") }})
UNION
(SELECT * FROM {{ ref("stg_os_moray") }})
UNION
(SELECT * FROM {{ ref("stg_os_north_ayrshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_north_lanarkshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_orkney") }})
UNION
(SELECT * FROM {{ ref("stg_os_perth_and_kinros") }})
UNION
(SELECT * FROM {{ ref("stg_os_renfrewshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_scottish_borders") }})
UNION
(SELECT * FROM {{ ref("stg_os_shetland_isles") }})
UNION
(SELECT * FROM {{ ref("stg_os_south_ayrshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_south_lanarkshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_stirlingshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_west_dunbartonshire") }})
UNION
(SELECT * FROM {{ ref("stg_os_west_lothian") }})
UNION
(SELECT * FROM {{ ref("stg_os_western_isles") }})
