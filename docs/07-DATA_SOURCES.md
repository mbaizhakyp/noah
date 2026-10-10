# 07 — Data Sources

Verified and working (each one fetched with real data, Oct 9, 2026). Coverage: Georgia.

## Flood and river forecasts
1. **NOAA NWPS reach streamflow** (National Water Model per reach: analysis, 18 h short-range, 10-day medium-range blend): `api.water.noaa.gov/nwps/v1/reaches/{id}/streamflow?series=`
2. **NOAA NWPS gauges** (flood categories + official river forecasts, 608 GA gauges): `api.water.noaa.gov/nwps/v1/gauges`
3. **NOAA HEFS ensemble river forecasts** (30-day probabilistic flow): `api.water.noaa.gov/hefs/v1/hydrograph-quantiles/`
4. **National Water Model files** (Google Cloud archive incl. 2024; AWS live): `storage.googleapis.com/national-water-model`, `noaa-nwm-pds`
5. **NWM Retrospective v3.0** (hourly reanalysis): `noaa-nwm-retrospective-3-0-pds`
6. **NOAA NWM / FIM map services** (18 h high-flow reaches, inundation extent, CatFIM): `maps.water.noaa.gov/server/rest/services/nwm/`
7. **NOAA OWP HAND + rating curves** (public CIROH bucket, per HUC8): `ciroh-owp-hand-fim.s3.amazonaws.com/hand_fim_4_9_9_0/`

## Rain and weather
8. **NOAA MRMS** (radar rain every 2 min, FLASH flash-flood nowcasts): `noaa-mrms-pds`
9. **Iowa State MRMS archive** (mirror): `mtarchive.geol.iastate.edu`
10. **NOAA Stage IV** (gauge-corrected rain totals): `mesonet.agron.iastate.edu/archive/data/.../stage4/`
11. **NOAA HRRR** (3 km rain forecast, 48 h): `noaa-hrrr-bdp-pds`
12. **NOAA National Blend of Models** (probabilistic forecast): `noaa-nbm-grib2-pds`
13. **NWS forecast gridpoints** (hourly QPF, 7 days): `api.weather.gov/gridpoints/`
14. **NDFD gridded QPF**: `tgftp.nws.noaa.gov/.../DC.ndfd/`
15. **WPC Excessive Rainfall Outlook** (Days 1–5): `mapservices.weather.noaa.gov/vector/rest/services/hazards/wpc_precip_hazards/MapServer`
16. **WPC rainfall forecast** (Days 1–7): `mapservices.weather.noaa.gov/vector/rest/services/precip/wpc_qpf/MapServer`
17. **Flash Flood Guidance** (rain needed to flood): `mapservices.weather.noaa.gov/raster/rest/services/precip/rfc_gridded_ffg/MapServer`
18. **NOAA Atlas 14** (rainfall rarity): `hdsc.nws.noaa.gov/cgi-bin/new/fe_text_mean.csv`
19. **NHC storm products** (track, cone, wind probabilities, storm surge): `nhc.noaa.gov/CurrentStorms.json`
20. **Open-Meteo** (point forecasts + archive): `api.open-meteo.com`

## Live alerts and observations
21. **NWS alerts** (flood / flash-flood warnings with polygons): `api.weather.gov/alerts/active?area=GA`
22. **USGS Water Data** (15-min river stage, flow, rain): `api.waterdata.usgs.gov/ogcapi/v0`
23. **USGS NWIS instantaneous values** (latest readings): `waterservices.usgs.gov/nwis/iv/`
24. **Synoptic weather stations** (289 GA rain gauges, live): `api.synopticdata.com/v2/stations/latest`
25. **Airport rain gauges, ASOS** (93 GA stations): `mesonet.agron.iastate.edu/cgi-bin/request/asos.py`
26. **CoCoRaHS** (daily volunteer rain): `data.cocorahs.org/export/exportreports.aspx`
27. **NWS Local Storm Reports** (street-level flood reports, live + 2005–2026 archive): `mesonet.agron.iastate.edu/geojson/lsr.geojson`
28. **NWS warning polygon archive**: `mesonet.agron.iastate.edu/geojson/sbw.geojson`
29. **NOAA Storm Events database**: `ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/`
30. **TomTom traffic incidents** (live closures, rain, flooding category): `api.tomtom.com/traffic/services/5/incidentDetails`
31. **Windy webcams** (2,467 GA cameras, live images): `api.windy.com/webcams/api/v3/webcams`
32. **Bluesky search** (public posts): `api.bsky.app/xrpc/app.bsky.feed.searchPosts`
33. **Google News RSS**: `news.google.com/rss/search`
34. **Mastodon hashtag timelines**: `/api/v1/timelines/tag/{tag}`

## Roads and routing
35. **OpenStreetMap Overpass**: `overpass-api.de/api/interpreter`
36. **Geofabrik Georgia extract** (daily): `download.geofabrik.de/north-america/us/georgia-latest.osm.pbf`
37. **Overture Maps transportation**: `s3://overturemaps-us-west-2/release/`
38. **GDOT road inventory** (every public road): `myfiles.dot.ga.gov/OTD/RoadAndTrafficData/Road_Inventory_Geodatabase.zip`
39. **GDOT functional class + bridges**: `maps.itos.uga.edu/arcgis/rest/services/GDOT/GDOT_FunctionalClass/MapServer`
40. **GDOT traffic counts 2008–2017**: `services5.arcgis.com/buITjRsK0rZsAXbQ/.../GDOT_AADT_and_TruckPct_2008to2017/FeatureServer/0`
41. **FHWA HPMS Georgia 2018** (road roughness, AADT): `geo.dot.gov/server/rest/services/Hosted/Georgia_2018_PR/FeatureServer/0`
42. **National Bridge Inventory**: `fhwa.dot.gov/bridge/nbi/2025/delimited/GA25.txt`
43. **Valhalla routing** (route around polygons): `valhalla1.openstreetmap.de/route`
44. **OSRM routing**: `router.project-osrm.org/route/v1/driving/`
45. **Nominatim geocoding**: `nominatim.openstreetmap.org/search`
46. **Photon geocoding**: `photon.komoot.io/api/`
47. **Census geocoder**: `geocoding.geo.census.gov/geocoder/`
48. **Google Maps directions links**: `google.com/maps/dir/?api=1`
49. **Apple Maps directions links**: `maps.apple.com/directions`

## Drainage, sewer, flood hazard
50. **Atlanta storm sewer GIS** (40,698 inlets, pipes, culverts): `egis.atlantaga.gov/arc/rest/services/MapWF/StormWater1/MapServer`
51. **Atlanta wastewater GIS** (sewer mains, CSO tunnel): `egis.atlantaga.gov/arc/rest/services/MapWF/WasteWater1c/MapServer`
52. **EPA ECHO CSO facilities** (12 in Atlanta): `echodata.epa.gov/echo/cwa_rest_services.get_facilities`
53. **Georgia EPD sewage spill reports** (last 30 days): `epd.georgia.gov`
54. **SeeClickFix** (flooding + pothole reports): `seeclickfix.com/api/v2/issues`
55. **FEMA flood zones (NFHL)**: `hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28`
56. **FEMA flood insurance claims (NFIP v3)**: `fema.gov/api/open/v3/NfipClaims`
57. **National Inventory of Dams**: `nid.sec.usace.army.mil/api/query`

## Road condition and imagery
58. **DeKalb street pavement condition**: `services2.arcgis.com/IxVN2oUE9EYLSnPE/.../Street_Pavement/FeatureServer/0`
59. **Atlanta repaving projects**: `services2.arcgis.com/zLeajbicrDRLQcny/.../Pavement_Projects/FeatureServer/0`
60. **Sandy Springs pavement index 2023**: `services5.arcgis.com/buITjRsK0rZsAXbQ/.../PCI_Scores_2023/FeatureServer/0`
61. **RDD2022 road-damage images**: figshare 21431547
62. **Mapillary street imagery**: `graph.mapillary.com`
63. **KartaView street photos**: `api.openstreetcam.org/2.0/photo/`

## Terrain, water, satellite
64. **USGS 3DEP 1 m lidar elevation**: `tnmaccess.nationalmap.gov/api/v1/products`
65. **USGS 3DEP seamless 10/30 m**: Planetary Computer `3dep-seamless`
66. **USGS Watershed Boundaries (WBD)**: `hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer`
67. **USGS NHDPlus HR** (streams, catchments): `hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer`
68. **USGS NLDI** (basins, upstream network): `api.water.usgs.gov/nldi/`
69. **Sentinel-1 radar** (Planetary Computer, Copernicus, ASF): `planetarycomputer.microsoft.com/api/stac/v1`
70. **NASA OPERA water maps** (DSWx-S1, DSWx-HLS, RTC-S1): NASA CMR
71. **Sentinel-2**: Planetary Computer `sentinel-2-l2a`
72. **Landsat**: Planetary Computer `landsat-c2-l2`
73. **Copernicus Global Flood Monitoring**: `stac.eodc.eu/api/v1/collections/GFM`
74. **NASA LANCE MODIS flood product**: NASA CMR `MCDWD_L3_F3_NRT`
75. **Maxar Open Data (Helene before/after)**: `maxar-opendata.s3.amazonaws.com/events/HurricaneHelene-Oct24/`
76. **NAIP aerial imagery**: Planetary Computer `naip`

## Population and community
77. **US Census ACS** (population, households without a car): `api.census.gov/data/2023/acs/acs5`
78. **CDC/ATSDR Social Vulnerability Index**: `onemap.cdc.gov/.../CDC_ATSDR_Social_Vulnerability_Index_2022_USA/FeatureServer`
79. **FEMA National Risk Index**: `services.arcgis.com/XG15cJAlne2vxtgt/.../National_Risk_Index_Counties/FeatureServer/0`
80. **USGS Structures** (hospitals, fire/EMS, schools): `carto.nationalmap.gov/arcgis/rest/services/structures/MapServer`
81. **Census TIGERweb counties**: `tigerweb.geo.census.gov/.../State_County/MapServer/1`
82. **Atlanta NPUs, neighborhoods, council districts**: `gis.atlantaga.gov/dpcd/rest/services/AdministrativeArea/GeopoliticalArea/FeatureServer`
