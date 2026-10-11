# Data sources

## Catastro: buildings (automatic)

- **Service:** INSPIRE WFS, `https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx`
- **Feature type:** `BU.BUILDINGPART` (carries floors; `BU.BUILDING` does not)
- **Limits:** 4 km² per bbox and 5,000 features per request, so `blm fetch` tiles at 500 m
- **CRS:** EPSG:25829 / 25830 / 25831 (UTM zones), 4326, 4258, 3857
- **Coverage:** all of Spain except Navarra and the Basque Country
- **Full municipality download (alternative):** ATOM feed `https://www.catastro.hacienda.gob.es/INSPIRE/buildings/ES.SDGC.BU.atom.xml`, updated twice a year
- **Docs:** <https://www.catastro.hacienda.gob.es/webinspire/index.html>

Manual check in a browser (replace the bbox):

```
https://ovc.catastro.meh.es/INSPIRE/wfsBU.aspx?service=wfs&version=2.0.0&request=getfeature&typenames=BU.BUILDINGPART&bbox=440200,4473400,440400,4473600&srsname=EPSG::25830
```

Save the response as `.gml` and run `blm fetch --from-files file.gml` if the service is unreachable from your machine. Save one small real response into `tests/fixtures/` (M1).

## PNOA LiDAR: heights (manual download)

1. Go to the CNIG download centre (`centrodedescargas.cnig.es`) → *Modelos digitales de elevaciones* → *LiDAR*.
2. Pick the most recent coverage that includes your area (2nd or 3rd coverage, classified point cloud, `.laz`).
3. Select tiles over your bbox (tiles are 2×2 km; one neighbourhood is usually 1–2 tiles).
4. Put the files in `data/raw/lidar/`, then run `make heights`.

**Valencia province shortcut (no form, no login):** the ICV publishes a 2015 LiDAR cloud as 2×2 km `.laz` sheets. The sheet index is a WFS (`https://terramapas.icv.gva.es/0301_2015PVAL0005_hojas?service=wfs&version=2.0.0&request=GetFeature&Typenames=distribucion_descargas&srsName=EPSG:25830&outputformat=geojsonstream`); each feature has a direct `link_laz`. CNIG's download centre blocks scripted access, so this was used for Ruzafa (sheets `724-4372`, `726-4372`, ~38 MB each).

Check: the tile CRS must match `epsg` in `config/area.yaml`, and the point classes must include 2 (ground) and 6 (building).

## INE income (Phase 1.5)

*Atlas de distribución de renta de los hogares*, by census section. Not used yet.

## Base map and aerial photo (web)

- Base map: OpenFreeMap (free, no key)
- Aerial: IGN PNOA orthophoto WMTS (`www.ign.es/wmts/pnoa-ma`)
