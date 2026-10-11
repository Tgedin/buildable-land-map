<?xml version="1.0" encoding="UTF-8"?>
<!-- Hand-made fixture shaped like a Catastro WFS BU.BUILDINGPART response.
     Replace with a real saved response once you have one (keep it small). -->
<gml:FeatureCollection
    xmlns:gml="http://www.opengis.net/gml/3.2"
    xmlns:wfs="http://www.opengis.net/wfs/2.0"
    xmlns:base="urn:x-inspire:specification:gmlas:BaseTypes:3.2"
    xmlns:bu-base="http://inspire.jrc.ec.europa.eu/schemas/bu-base/3.0"
    xmlns:bu-core2d="http://inspire.jrc.ec.europa.eu/schemas/bu-core2d/2.0"
    xmlns:bu-ext2d="http://inspire.jrc.ec.europa.eu/schemas/bu-ext2d/2.0">
  <gml:featureMember>
    <bu-ext2d:BuildingPart gml:id="ES.SDGC.BU.1234501VK4713S_part1">
      <bu-core2d:inspireId>
        <base:Identifier>
          <base:localId>1234501VK4713S_part1</base:localId>
          <base:namespace>ES.SDGC.BU</base:namespace>
        </base:Identifier>
      </bu-core2d:inspireId>
      <bu-ext2d:geometry>
        <bu-core2d:BuildingGeometry2D>
          <bu-core2d:geometry>
            <gml:Surface gml:id="Surface_1" srsName="urn:ogc:def:crs:EPSG::25830">
              <gml:patches>
                <gml:PolygonPatch>
                  <gml:exterior>
                    <gml:LinearRing>
                      <gml:posList srsDimension="2">440300 4473500 440314 4473500 440314 4473516 440300 4473516 440300 4473500</gml:posList>
                    </gml:LinearRing>
                  </gml:exterior>
                  <gml:interior>
                    <gml:LinearRing>
                      <gml:posList srsDimension="2">440305 4473505 440309 4473505 440309 4473509 440305 4473509 440305 4473505</gml:posList>
                    </gml:LinearRing>
                  </gml:interior>
                </gml:PolygonPatch>
              </gml:patches>
            </gml:Surface>
          </bu-core2d:geometry>
        </bu-core2d:BuildingGeometry2D>
      </bu-ext2d:geometry>
      <bu-ext2d:numberOfFloorsAboveGround>6</bu-ext2d:numberOfFloorsAboveGround>
      <bu-ext2d:numberOfFloorsBelowGround>1</bu-ext2d:numberOfFloorsBelowGround>
    </bu-ext2d:BuildingPart>
  </gml:featureMember>
  <gml:featureMember>
    <bu-ext2d:BuildingPart gml:id="ES.SDGC.BU.1234501VK4713S_part2">
      <bu-core2d:inspireId>
        <base:Identifier>
          <base:localId>1234501VK4713S_part2</base:localId>
        </base:Identifier>
      </bu-core2d:inspireId>
      <bu-ext2d:geometry>
        <bu-core2d:BuildingGeometry2D>
          <bu-core2d:geometry>
            <gml:Surface gml:id="Surface_2">
              <gml:patches>
                <gml:PolygonPatch>
                  <gml:exterior>
                    <gml:LinearRing>
                      <gml:posList srsDimension="2">440314 4473500 440320 4473500 440320 4473516 440314 4473516 440314 4473500</gml:posList>
                    </gml:LinearRing>
                  </gml:exterior>
                </gml:PolygonPatch>
              </gml:patches>
            </gml:Surface>
          </bu-core2d:geometry>
        </bu-core2d:BuildingGeometry2D>
      </bu-ext2d:geometry>
      <bu-ext2d:numberOfFloorsAboveGround>2</bu-ext2d:numberOfFloorsAboveGround>
      <bu-ext2d:numberOfFloorsBelowGround xsi:nil="true" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
    </bu-ext2d:BuildingPart>
  </gml:featureMember>
</gml:FeatureCollection>
