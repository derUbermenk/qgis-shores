'''
from qgis.core import *

myLayer: QgsVectorLayer = iface.activeLayer()

myLayer.selectAll()

feat_ids = myLayer.selectedFeatureIds()
feats = myLayer.selectedFeatures()

feat_ids.reverse()
feats.reverse()

print(feats[0].geometry())
intersection = feats[0].geometry().intersection(feats[1].geometry()).asMultiPoint()[0]

origin = feats[0].geometry().asPolyline()[0]
print("origin: ", origin)

distance = origin.distance(intersection)
print("distance: ", distance)
'''

class A:
  @classmethod
  def x(
    cls,
    a
  ):
    return a

  @classmethod
  # this is rabbit
  def s(
    cls,
    b
  ):
    print("hello")
    return b

print(A.x(1))
print(A.s(1))