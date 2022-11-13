import pandas as pd
import math

from qgis.core import *

#####---------------------------DEFINE VARIABLES HERE-----------------------------------####
transects_time_series: str = ''
normals: str = ''
#####---------------------------END-------------------------------------------------####

class CoastSatParser:
  def __init__(self, transect_time_series_file_name, normals_filename) -> None:
    self.crs: QgsCoordinateReferenceSystem = QgsProject.instance().crs()

    self.project_path = QgsProject.instance().homePath()
    self.transect_time_series_file_path  = self.project_path + "/intersects/" + transect_time_series_file_name
    self.normals_file_path = normals_filename = self.project_path + "/transects/" + normals_filename

  def load_normals(self):
    normals = QgsVectorLayer(
      self.normals_file_path,
      "transects_layer",
      "ogr"
    )

    return normals 

  def load_transect_time_series(self):
    transect_ts = pd.read_csv(self.transect_time_series_file_path, index_col=0)

    return transect_ts

  def initialize_writer(self):
    coastCR_fields = QgsFields()
    coastCR_fields.append(QgsField("ID_Profile", QVariant.Int))
    coastCR_fields.append(QgsField("ID_Coast", QVariant.Int))
    coastCR_fields.append(QgsField("Distance", QVariant.Double))

    writer = QgsVectorFileWriter(
      self.project_path + "/intersects/" + "intersects.shp",
      "UTF-8",
      coastCR_fields,
      QgsWkbTypes.Point,
      srs = self.crs,
      driverName="ESRI Shapefile"
    )

    return writer

  def run(self):
    writer = self.initialize_writer()
    normals = self.load_normals().getFeatures()
    transect_ts = self.load_transect_time_series()

    transect_names = transect_ts.columns[1:]

    for normal in normals:
      normal_geom = normal.geometry()

      intersects = transect_ts[ transect_names[normal.id()] ]

      for (id_coast, intersect) in enumerate(intersects):
        feature = QgsFeature()

        if math.isnan(intersect) == False:
          point = normal_geom.interpolate(intersect)
          feature.setGeometry(point)

          feature.setAttributes(
            [
              normal.id(),
              id_coast,
              intersect
            ]
          )

          writer.addFeature(feature)

    del writer
    print('done')

csP = CoastSatParser(transects_time_series, normals)
csP.run()
