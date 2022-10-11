from pyscripts.TransectGenerator import TransectGenerator
from qgis.core import *

#####---------------------------DEFINE NAMES HERE-----------------------------------####
landward_baseline_name = "landward_baseline0" # define name here
seaward_baseline_name = "seaward_baseline0" # define name here
#####---------------------------END-------------------------------------------------####

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