from dataclasses import Field
from math import nan
from qgis.core import *

def myQChainage(baseline: QgsVectorLayer, baseline_positions: int, spacing: float, writer: QgsVectorFileWriter):
  query_string = '"id_pos"={position}'.format(position=baseline_positions)
  baseline.selectByExpression(query_string, QgsVectorLayer.SetSelection)

  lw_baseline = baseline.selectedFeatures()[0]
  lw_geom = lw_baseline.geometry()

  current_point_distance = 0
  index = 0

  while current_point_distance <= lw_geom.length():
    point = lw_geom.interpolate(current_point_distance)

    fet = QgsFeature()
    fet.setGeometry(point)
    fet.setAttributes([index, current_point_distance])

    writer.addFeature(fet)

    index+=1
    current_point_distance+=spacing

  del writer
  print('chainage done')

def myTransect(landward_points: QgsVectorLayer, seaward_points: QgsVectorLayer, writer: QgsVectorFileWriter):
  lw_points = landward_points.getFeatures()
  sw_index= QgsSpatialIndex(seaward_points.getFeatures())

  # for point lw_points, get nearest neighbor and generate a transect line 
  id = 0
  for point_feature in lw_points:
    point_geometry = point_feature.geometry().asPoint()

    nearest_sw = sw_index.nearestNeighbor(point_geometry, 1)
    seaward_points.selectByIds(nearest_sw)
    nearest_sw = seaward_points.selectedFeatures()[0].geometry().asPoint()

    #

    # create a feature
    fet = QgsFeature()
    fet.setGeometry(QgsGeometry.fromPolylineXY([point_geometry, nearest_sw]))
    fet.setAttributes([id])

    writer.addFeature(fet)
    id += 1
  
  del writer
  print('done')

def myTransectV2(landward_points: QgsVectorLayer, seaward_baseline: QgsGeometry, writer: QgsVectorLayer):
  lw_points = landward_points.getFeatures()

  for lw_point in lw_points: 
    shortest_line = lw_point.geometry().shortestLine(seaward_baseline) # is multiline string
    
    fet = QgsFeature()
    fet.setGeometry(shortest_line)

    writer.addFeature(fet)

  del writer
  print('transect generation done')


def calculateIntersections(transects: QgsVectorLayer, shorelines: QgsVectorLayer, intersect_structure_coastsat: QgsVectorFileWriter, intersect_structure_coastcr: QgsVectorFileWriter): 
  shorelines_ = shorelines.getFeatures()

  for shoreline in shorelines_:
    intersects = [nan] * len(transects) 

    fet = QgsFeature()
    for transect in transects.getFeatures():
      # cases intersection point can be
      #   empty line string if no connection        // check isEmpty
      #   point if only one intersection
      #   multipoint if more than one intersection
      #   if many intersection intersection_point is multipoint and points are ordered in increasing distance from vertex origin
      intersection_point = transect.geometry().intersection(shoreline.geometry())

      # check if empty
      if intersection_point.isEmpty():
        pass
      elif QgsWkbTypes.isSingleType(intersection_point.wkbType()):
        # check if single type
        origin = transect.geometry().asMultiPolyline()[0][0]
        intersection_point = intersection_point.asPoint()
        distance = origin.distance(intersection_point)

        intersects[transect.id()] = distance 

        fet_ = QgsFeature()
        fet.setAttributes([transect.id(), shoreline.id()])
        point_ = transect.geometry().interpolate(distance)
        fet.setGeometry(point_)
        intersect_structure_coastcr.addFeature(fet)

      else:
        # assume multitype
        origin = transect.geometry().asMultiPolyline()[0][0]
        intersection_point = intersection_point.asMultiPoint()[0]
        distance = origin.distance(intersection_point)

        intersects[transect.id()] = distance 

        fet_ = QgsFeature()
        fet.setAttributes([transect.id(), shoreline.id()])
        point_ = transect.geometry().interpolate(distance)
        fet.setGeometry(point_)
        intersect_structure_coastcr.addFeature(fet)
      
    fet.setAttributes([shoreline.id()] + intersects)
    intersect_structure_coastsat.addFeature(fet)

  del intersect_structure_coastsat
  del intersect_structure_coastcr
  print('intersect calculation done')


# generate landward baseline
def run_landwardBaseline():
  home_dir: str = QgsProject.instance().homePath()
  project_crs: QgsCoordinateReferenceSystem = QgsCoordinateReferenceSystem("EPSG:3124")
  geometry_type = QgsWkbTypes.Point

  layer_name = 'baseline_0'

  fields = QgsFields()
  fields.append(QgsField("id", QVariant.Int))
  fields.append(QgsField("distance", QVariant.String))

  writer: QgsVectorFileWriter = QgsVectorFileWriter(
    home_dir+"/"+"transects"+"/"+"landward_points.shp",
    "UTF-8",
    fields,
    geometry_type, 
    srs = project_crs,
    driverName = "ESRI Shapefile"
  )

  baseline = QgsProject.instance().mapLayersByName(layer_name)[0]
  myQChainage(baseline, 0, 10, writer)

# generate seaward baseline
def run_seawardBaseline():
  home_dir: str = QgsProject.instance().homePath()
  project_crs: QgsCoordinateReferenceSystem = QgsCoordinateReferenceSystem("EPSG:3124")
  geometry_type = QgsWkbTypes.Point

  layer_name = 'baseline_0'

  fields = QgsFields()
  fields.append(QgsField("id", QVariant.Int))
  fields.append(QgsField("distance", QVariant.String))

  writer: QgsVectorFileWriter = QgsVectorFileWriter(
    home_dir+"/"+"transects"+"/"+"seaward_points.shp",
    "UTF-8",
    fields,
    geometry_type, 
    srs = project_crs,
    driverName = "ESRI Shapefile"
  )

  baseline = QgsProject.instance().mapLayersByName(layer_name)[0]
  myQChainage(baseline, 1, 0.5, writer)

  # load layer to project

# generate transects
def run_genTransects():

  home_dir: str = QgsProject.instance().homePath()
  project_crs: QgsCoordinateReferenceSystem = QgsCoordinateReferenceSystem("EPSG:3124")
  geometry_type = QgsWkbTypes.LineString

  fields = QgsFields()
  fields.append(QgsField("id", QVariant.Int))

  writer: QgsVectorFileWriter = QgsVectorFileWriter(
    "{homedir}/{output_folder}/{output_name}".format(homedir=home_dir, output_folder="transects", output_name="transects.shp"),
    "UTF-8",
    fields,
    geometry_type,
    srs = project_crs,
    driverName = "ESRI Shapefile"
  )

  landward_points = QgsVectorLayer(home_dir+"/"+"transects"+"/"+"landward_points.shp", "landward_points", "ogr")
  seaward_points = QgsVectorLayer(home_dir+"/"+"transects"+"/"+"seaward_points.shp", "seaward_baseline", "ogr")

  myTransect(landward_points, seaward_points, writer)

def run_genTransects_2():
  home_dir: str = QgsProject.instance().homePath()
  project_crs: QgsCoordinateReferenceSystem = QgsCoordinateReferenceSystem("EPSG:3124")
  geometry_type = QgsWkbTypes.LineString

  fields = QgsFields()
  fields.append(QgsField("id", QVariant.Int))

  writer: QgsVectorFileWriter = QgsVectorFileWriter(
    "{homedir}/{output_folder}/{output_name}".format(homedir=home_dir, output_folder="transects", output_name="transects_v2.shp"),
    "UTF-8",
    fields,
    geometry_type,
    srs = project_crs,
    driverName = "ESRI Shapefile"
  )

  landward_points = QgsVectorLayer(home_dir+"/"+"transects"+"/"+"landward_points.shp", "landward_points", "ogr")

  baseline: QgsVectorLayer = QgsProject.instance().mapLayersByName("baseline_0")[0]
  query_string = '"id_pos"={position}'.format(position=1)
  baseline.selectByExpression(query_string, QgsVectorLayer.SetSelection)

  myTransectV2(landward_points, baseline.selectedFeatures()[0].geometry(), writer)

def run_CalculateIntersects():
  home_dir: str = QgsProject.instance().homePath()
  project_crs: QgsCoordinateReferenceSystem = QgsCoordinateReferenceSystem("EPSG:3124")
  transects = QgsVectorLayer(home_dir + "/" + "transects" + "/" + "transects_v2.shp", "transects_v2", "ogr")
  shorelines = QgsVectorLayer(home_dir + "/" + "positions" + "/" + "dummy_position.shp", "shorelines", "ogr")

  coastSatFields = QgsFields()
  coastSatFields.append(QgsField("shorelineID", QVariant.Int))
  for transect in transects.getFeatures():
    coastSatFields.append(QgsField("T{tID}".format(tID=transect.id()), QVariant.Double))


  coastSatLikeWriter = QgsVectorFileWriter(
    "{homedir}/{output_folder}/{output_name}".format(homedir=home_dir, output_folder="intersects", output_name="coastSatLikeIntersects.shp"),
    "UTF-8",
    coastSatFields,
    QgsWkbTypes.Unknown,
    srs = project_crs,
    driverName = "ESRI Shapefile"
  )

  coastCRFields = QgsFields()
  coastCRFields.append(QgsField("transect_id", QVariant.Int))
  coastCRFields.append(QgsField("shoreline_id", QVariant.Int))

  coastCRLikeWriter = QgsVectorFileWriter(
    "{homedir}/{output_folder}/{output_name}".format(homedir=home_dir, output_folder="intersects", output_name="coastCRLikeIntersects.shp"),
    "UTF-8",
    coastCRFields,
    QgsWkbTypes.Point,
    srs = project_crs,
    driverName = "ESRI Shapefile"
  )

  calculateIntersections(transects, shorelines, coastSatLikeWriter, coastCRLikeWriter)

run_landwardBaseline()
run_seawardBaseline()

# run_genTransects()
run_genTransects_2()

run_CalculateIntersects()