import os

from typing import List
from numpy import outer
from qgis.core import *

#####---------------------------DEFINE NAMES HERE-----------------------------------####
landward_baseline_name = "landward_baseline0" # define name here
seaward_baseline_name = "seaward_baseline0" # define name here
#####---------------------------END-------------------------------------------------####

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


class TransectGenerator:
  def __init__(
    self, 
    landward_baseline: QgsVectorLayer,
    seaward_baseline: QgsVectorLayer,
    spacing_m: int = 5,
    output_path: str = "transects", 
    crs: QgsCoordinateReferenceSystem = QgsProject.instance().crs()
  ) -> None:
    self.landward_baseline = landward_baseline
    self.seaward_baseline = seaward_baseline
    self.spacing = spacing_m 
    self.crs = crs
    self.output_path= TransectUtility.format_output_path(output_path)

  # creates equally spaced points in landward baseline
  # ... spaced in meters defined by the spacing attribute
  def generateTransectOrigins(self) -> List[QgsPointXY]: 
    # get the landward baseline
    # assumes only one feature (landward baseline line) in the landward baseline layer
    # then get the geometry of the baseline
    #
    # start with distance of 0, keep increasing the distance by the spacing until
    # the distance is greater than the lenght of the baseline geometry, all the while
    # interpolating to get the point associated with the interpolation of the given distance
    transect_origins: List[QgsPointXY] = []
    lw_baseline_geometry = TransectUtility.extract_geometries(self.landward_baseline)[0]

    current_distance = 0
    while current_distance <= lw_baseline_geometry.length():
      point = lw_baseline_geometry.interpolate(current_distance).asPoint()
      transect_origins.append(point)

      current_distance += self.spacing
    
    return transect_origins

  # generates a list of all shortest lines from a transect 
  # ... origin to the seaward baseline
  def generateTransects(self, transect_origins: List[QgsPointXY]) -> List[QgsMultiLineString]:
    print('generating transects')
    # get the seaward baseline
    # assume only one feature in seaward baseline which is the seaward baseline
    # then get the geometry
    transects : List[QgsMultiLineString] = []
    sw_baseline_geom = TransectUtility.extract_geometries(self.seaward_baseline)[0]

    for transect_origin in transect_origins:
      transect = QgsGeometry.fromPointXY(transect_origin).shortestLine(sw_baseline_geom)
      transects.append(transect)
    
    print('done generating transects')
    return transects
  
  # saves the transect origins to a shape file
  def saveTransectOrigins(self, transect_origins: List[QgsPointXY]):
    output_fileName: str = "transectOrigins_{basename}.shp".format(basename=self.landward_baseline.name())
    geometry_type = QgsWkbTypes.Point
    fields: QgsFields = QgsFields()
    srs = QgsProject.instance().crs()

    writer = TransectUtility.init_shpWriter(
      self.output_path,
      output_fileName,
      geometry_type,
      fields,
      srs
    )

    for transect_origin in transect_origins:
      fet = QgsFeature()
      fet.setGeometry(QgsGeometry.fromPointXY(transect_origin))

      writer.addFeature(fet)
    
    del writer

  # saves the transects to a shpae file
  def saveTransects(self, transect_list: List[QgsMultiLineString]):
    output_fileName: str = "transects_{basename}.shp".format(basename=self.landward_baseline.name())
    geometry_type = QgsWkbTypes.LineString
    fields: QgsFields = QgsFields()
    srs = QgsProject.instance().crs()

    writer = TransectUtility.init_shpWriter(
      self.output_path,
      output_fileName,
      geometry_type,
      fields,
      srs
    )

    for transect in transects:
      fet = QgsFeature()
      fet.setGeometry(QgsGeometry.fromMultiPolylineXY(transect))

      writer.addFeature(fet)
    
    del writer


  def run(self):
    transect_origins = self.generateTransectOrigins() 
    transects = self.generateTransects(transect_origins)

    TransectUtility.init_output_path(self.output_path)

    self.saveTransectOrigins(transect_origins)
    self.saveTransects(transects)

    print('transects generated')

project = QgsProject.instance() 
landward_baseline = project.mapLayersByName(landward_baseline_name)
seaward_baseline = project.mapLayersByName(seaward_baseline_name)

if landward_baseline == [] and seaward_baseline == []:
  print('check layer names. all layers not detected')
elif landward_baseline == []:
  print('check landward baseline name. layer not detected')
elif seaward_baseline == []:
  print('check seaward baseline name. layer not detected')
else:
  landward_baseline_ = landward_baseline[0]
  seaward_baseline_ = seaward_baseline[0]
  t = TransectGenerator(
    landward_baseline_,
    seaward_baseline_,
    5
  )

  t.run() 