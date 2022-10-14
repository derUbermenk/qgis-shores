from tokenize import String
from qgis.core import *
from qgis.PyQt.QtCore import QVariant 
from typing import List
from math import nan

# --- DEFINE VARIABLES HERE --- # 

transect_fileName = "transects_landward_baseline0.shp"
shoreline_fileName = "dummy_position.shp"

# -------- END ------- #

# recommended file structure
# ... .
# ... ├── aoi
# ... ├── intersects
# ... │   ├── coastCR
# ... │   └── coastSat
# ... ├── positions
# ... ├── pyscripts
# ... │   └── __pycache__
# ... └── transects

#
# Use 2 types of intersection
# CoastCR like is needed for calculation in CoastCR
# CoastSat for easy calculations in QGIS
# Intersection table structure
# ... CoastSat like:
# ... ... date: string, transect_name_1: string, transect_name_2: string ... transect_name_i: string
# 
# ... CoastCR like:
# ... ... coast_id: int, transect_id: int 
# 
# each feature in CoastSat does not have a geometry
# each feature in CoastCR is a point, representing the point of intersection between a
# coastline position and a transect
#

class TransectUtility:
  @classmethod
  def format_output_path(cls, output_dirname: str):
    file_path = "{homepath}/{output_directory}".format(
      homepath=QgsProject.instance().homePath(),
      output_directory=output_dirname
    )
    return file_path

  @classmethod
  # extracts the features from a layer
  def extract_features(cls, layer: QgsVectorLayer) -> List[QgsFeature]:
    features = [feature for feature in layer.getFeatures()]
    return features 

  @classmethod
  # extracts the geometries from a layer
  def extract_geometries(cls, layer: QgsVectorLayer) -> List[QgsGeometry]:
    geometries = [feature.geometry() for feature in layer.getFeatures()]
    return geometries

  @classmethod
  # writes shape files
  def init_shpWriter(
    cls,
    output_path: str,
    output_fileName: str,
    geometry_type,  # QgsWkbTypes
    fields: QgsFields,
    srs: QgsCoordinateReferenceSystem, 
  ) -> QgsVectorFileWriter:
    output_filePath = "{output_path}/{output_fileName}".format(
      output_path=output_path,
      output_fileName=output_fileName
    )

    writer = QgsVectorFileWriter(
      output_filePath,
      "UTF-8",
      fields,
      geometry_type,
      srs=srs,
      driverName = "ESRI Shapefile"
    )

    return writer


  @classmethod
  def init_output_path(
    cls,
    output_path: str
  ):
    isExists = os.path.exists(output_path)

    if isExists == False: 
      # create dir
      os.makedirs(output_path)

class IntersectFinder:

  def __init__(
    self,
    transect_fileName,
    shoreline_fileName,
    project_crs = QgsProject.instance().crs()
    ) -> None:
    self.crs: QgsCoordinateReferenceSystem =project_crs 

    self.project_path = QgsProject.instance().homePath()
    self.transects_layer_filePath: str = self.project_path  + "/transects/" + transect_fileName
    self.shorelines_layer_filePath: str = self.project_path + "/positions/" + shoreline_fileName 
    self.coastSat_output_path: str = self.project_path + "/intersects/coastSat" 
    self.coastCR_output_path: str= self.project_path + "/intersects/coastCR"

    # initialize output paths here
    TransectUtility.init_output_path(self.coastSat_output_path)
    TransectUtility.init_output_path(self.coastCR_output_path)

    
  # finds the intersections for all transects and shorelines
  def findIntersections(self,
    transects: List[QgsFeature],
    shorelines: List[QgsFeature],
    coastCR_writer: QgsVectorFileWriter,
    coastSat_writer: QgsVectorFileWriter
  ):

    for shoreline in shorelines:
      intersections = [nan] * len(transects)

      coastSat_fet = QgsFeature()
      for (indx, transect) in enumerate(transects):
        # cases:
        # ... no intersection: intersection_point.isEmpty() == true
        # ... one intersection: singleType as Point
        # ... two or more intersections: multitype as Multipoint
        transect = transect.geometry()
        origin: QgsGeometry = transect.asMultiPolyline()[0][0]
        intersection_point: QgsGeometry = transect.geometry().intersection(shoreline.geometry)

        if intersection_point.isEmpty():
          # no intersection point detected
          # ... do nothing, keep the intersection point as nan in coastsat structure
          # ... and not add the feature in coastcr structure
          pass
        elif QgsWkbTypes.isSingleType(intersection_point.wkbType()):
          # one intersection point is detected
          # ... intersection is of type QgsGeometry:Point can be cast as point
          intersection_point = intersection_point.asPoint()
        else: # assume multitype
          # multiple intersections between transect and shoreline 
            # ... intersection if of type QgsGeometry:Multipoint and can be cast as multipoint 
            # ... get only first intersection 
            # 
            # When multiple intersections, geometry1.intersection(geometry2) returns geometry 
            # ... that can be cast as multipoint. When done so multipoint can be interpreted
            # ... as [
            # ...     intersection_1: QgsGeometry:Point, 
            # ...     intersection2: QgsGeometry:Point ... intersection_i: QgsGeometry:Point
            # ...    ]
            # ... where intersection_1 is the closest intersection from the origin of geometry 1
            # ... and intersection_i is the farthest intersection.
            #
            # Get intersection_1 (closest to origin) by CoastCR standards on onshore 
            # ... baseline approach

          intersection_point = intersection_point.asMultiPoint()[0]
        
        # then calculate the distance from origin
        distance = origin.distance(intersection_point)
        intersections[indx] = distance

        # then write to CoastCR like writer
        coastCR_fet = QgsFeature()
        coastCR_intersect_fet_geom = transect.interpolate(distance)
        coastCR_fet.setAttributes([transect.id(), shoreline.id()])
        coastCR_fet.setGeometry(coastCR_intersect_fet_geom)

        coastCR_writer.addFeature(coastCR_fet)

      # then write intersection distances to CoastSat like writer  
      coastSat_writer.addFeature([shoreline.id()] + intersections)
      # coastSat_writer.addFeature([shoreline.date()] + intersections)  # get shoreline date attribute

    del coastCR_writer
    del coastSat_writer
    print('intesrect calculation done!')


  def run(self):
    # transects_layer = load transects layer
    # shorelines_layer = load shorelines layer
    transects_layer = QgsVectorLayer(
      self.transects_layer_filePath,
      "transects_layer",
      "ogr"
    )

    shorelines_layer = QgsVectorLayer(
      self.shorelines_layer_filePath,
      "shorelines_layer",
      "ogr"
    )

    # transects = extract transect_layer features
    transects = TransectUtility.extract_features(transects_layer) 

    # shorelines = extract transect_layer features 
    shorelines = TransectUtility.extract_features(shorelines_layer)

    coastCR_fields = QgsFields()
    coastCR_fields.append(QgsField("ID_Profile", QVariant.Int))
    coastCR_fields.append(QgsField("ID_Coast", QVariant.Int))
    coastCR_fields.append(QgsField("Distance", QVariant.Double))

    # initialize coastSat and CoastCR writers
    # !!! fix naming conventions
    coastCR_writer = QgsVectorFileWriter(
      self.coastCR_output_path + "/" + "coastCR_intersects.shp",
      "UTF-8",
      coastCR_fields,
      QgsWkbTypes.Point,
      srs = QgsProject.instance().crs(),
      driverName="ESRI Shapefile"
    )

    coastSat_fields = QgsFields()
    coastSat_fields.append(QgsField("dates", QVariant.String))
    for transect in transects:
      coastSat_fields.append(QgsField("T{tID}".format(tID=transect.id()), QVariant.Double))
      # where each column is a transect and each row is the distance 
      # ... for a particular shoreline date

    coastSat_writer = QgsVectorFileWriter(
      self.coastSat_output_path + "/" + "coastSat_intersects.shp",
      "UTF-8",
      coastSat_fields,
      QgsWkbTypes.Unknown,
      srs = QgsProject.instance().crs(),
      driverName="ESRI Shapefile"
    )

    # to do: move finding and saving 
    # ... intersections to different methods?
    #
    # self.findIntersections finds and saves at the same time
    # ... fast but hard to read
    self.findIntersections(
      transects,
      shorelines,
      coastCR_writer,
      coastSat_writer
    )

# -- run -- #
ifn = IntersectFinder(
  transect_fileName,    
  shoreline_fileName
)

ifn.run()
