import os

from typing import List
from numpy import outer
from qgis.core import *
from geojson import Feature, LineString, FeatureCollection

#####---------------------------DEFINE VARIABLES HERE-----------------------------------####
landward_baseline_name = "lw_baseline" # define name here
seaward_baseline_name = "sw_baseline" # define name here
spacing = 20 # transect origin spacing in meters
#####---------------------------END-------------------------------------------------####

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
    lw_baseline_geometry = TransectUtility.extract_geometries(
      self.landward_baseline
    )[0]

    current_distance = 0
    while current_distance <= lw_baseline_geometry.length():
      point = lw_baseline_geometry.interpolate(current_distance).asPoint()
      transect_origins.append(point)

      current_distance += self.spacing
    
    return transect_origins

  # generates a list of all shortest lines from a transect 
  # ... origin to the seaward baseline
  def generateTransects(self, transect_origins: List[QgsPointXY]) -> List[QgsLineString]:
    # get the seaward baseline
    # assume only one feature in seaward baseline which is the seaward baseline
    # then get the geometry
    transects : List[QgsLineString] = []
    sw_baseline_geom = TransectUtility.extract_geometries(self.seaward_baseline)[0]

    for transect_origin in transect_origins:
      transect = QgsGeometry.fromPointXY(transect_origin).shortestLine(sw_baseline_geom).asPolyline()
      transects.append(transect)
    
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
  def saveTransects(self, transects: List[QgsMultiLineString]):
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
      # feature geometry will be set to multipolyline 
      # ... once accessed from layer
      fet.setGeometry(QgsGeometry.fromPolylineXY(transect))

      writer.addFeature(fet)
    
    del writer

  def save_asGeojson(self, transects: List[QgsGeometry]):
    feats: List[Feature] = []

    for (transect_indx, transect) in enumerate(transects):
      transect_name = "T{indx}".format(indx=transect_indx)
      transect_geometry = transect

      properties = {"name": transect_name}
      geometry=LineString([(transect[0].x(), transect[0].y()), (transect[1].x(), transect[1].y())])
      feature = Feature(geometry=geometry, properties=properties)

      feats.append(feature)
    

    crs_info = ['EPSG', 3124]
    crs_name = "urn:ogc:def:crs:{authority}::{code}".format(authority=crs_info[0], code=crs_info[1])
    feature_collection = FeatureCollection(
      crs={ "type": "name", "properties": { "name": crs_name } },
      features=feats
    )

    geojson_filename = QgsProject.instance().baseName() + '.geojson'
    output_path = QgsProject.instance().homePath() + '/transects/' + geojson_filename

    with open(output_path, "w") as text_file:
      text_file.write("{0}".format(feature_collection))



  def run(self):
    transect_origins = self.generateTransectOrigins() 
    transects_unfiltered = self.generateTransects(transect_origins)
    transects = self.filterTransects(transect_origins, transects_unfiltered)

    TransectUtility.init_output_path(self.output_path)

    self.saveTransectOrigins(transect_origins)
    self.saveTransects(transects)
    self.save_asGeojson(transects)
    print('transects generated!')

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
    spacing
  )

  t.run() 