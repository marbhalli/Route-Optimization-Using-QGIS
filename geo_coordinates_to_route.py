# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import pandas as pd

import numpy as np

import sys

from qgis.core import *

qgs = QgsApplication([], False)

QgsApplication.setPrefixPath("/Applications/QGIS.app/Contents/MacOS", True)

qgs.initQgis()

sys.path.append('/Applications/QGIS.app/Contents/Resources/python/plugins')

import processing

from processing.core.Processing import Processing

Processing.initialize()

from QNEAT3.Qneat3Provider import Qneat3Provider

provider = Qneat3Provider()

QgsApplication.processingRegistry().addProvider(provider)


def add_raster():
    uri="type=xyz&url=https://mt1.google.com/vt/lyrs%3Dm%26x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D&zmax=19&zmin=0"
    mts_layer=QgsRasterLayer(uri,'Google Maps','wms')
    if not mts_layer.isValid():
        print ("Layer failed to load!")
    QgsProject.instance().addMapLayer(mts_layer)

def add_points():
    uri = f"file:///Users/muhammadabdul/Desktop/Work/route_optimization/new_attempt/optimized_route.csv?encoding=%s&delimiter=%s&xField=%s&yField=%s&crs=%s" % (
    "UTF-8", ",", "longitude", "latitude", "epsg:3857")

    # Make a vector layer
    eq_layer = QgsVectorLayer(uri, f"destinations", "delimitedtext")

    # Check if layer is valid
    if not eq_layer.isValid():
        print("Layer not loaded")

    # Add CSV data
    QgsProject.instance().addMapLayer(eq_layer)

    symbol = QgsMarkerSymbol.createSimple({'name': 'circle', 'color': 'blue', 'size': 5})
    eq_layer.renderer().setSymbol(symbol)

    layer_settings = QgsPalLayerSettings()
    text_format = QgsTextFormat()

    text_format.setFont(QFont("Arial", 20))
    text_format.setSize(20)

    buffer_settings = QgsTextBufferSettings()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(1)
    buffer_settings.setColor(QColor("white"))

    text_format.setBuffer(buffer_settings)
    layer_settings.setFormat(text_format)

    layer_settings.fieldName = "field_1"
    layer_settings.placement = 2

    layer_settings.enabled = True

    layer_settings = QgsVectorLayerSimpleLabeling(layer_settings)
    eq_layer.setLabelsEnabled(True)
    eq_layer.setLabeling(layer_settings)
    eq_layer.triggerRepaint()

    return eq_layer.extent()

def OD_matrix():
    processing.run("qneat3:OdMatrixFromPointsAsCsv",
                   {'INPUT': '/Users/muhammadabdul/Desktop/Work/NTRC_Lahore-Road-Network/Lahore_District.shp',
                    'POINTS': 'delimitedtext://file:///Users/muhammadabdul/Desktop/Work/route_optimization/new_attempt/destinations.csv?type=csv&maxFields=10000&detectTypes=yes&xField=longitude&yField=latitude&crs=EPSG:3857&spatialIndex=no&subsetIndex=no&watchFile=no',
                    'ID_FIELD': 'field_1', 'STRATEGY': 0, 'ENTRY_COST_CALCULATION_METHOD': 0,
                    'DIRECTION_FIELD': 'direction', 'VALUE_FORWARD': '1', 'VALUE_BACKWARD': '1', 'VALUE_BOTH': '0',
                    'DEFAULT_DIRECTION': 2, 'SPEED_FIELD': '', 'DEFAULT_SPEED': 5, 'TOLERANCE': 0,
                    'OUTPUT': '/Users/muhammadabdul/Desktop/Work/route_optimization/new_attempt/df_OD.csv'})


    df_OD = pd.read_csv('/Users/muhammadabdul/Desktop/Work/route_optimization/new_attempt/df_OD.csv', delimiter=';')

    return df_OD
#
def optimized_df(df_OD,total_destinations,geo_coordinates):
    traversed_latlng = []
    distance_op = 0.0
    start = 0
    optimized_route = []
    optimized_route.append(start)
    for i in range(1, total_destinations):
        temp_min = df_OD.groupby('origin_id').get_group(start).query(
            "destination_id!=@traversed_latlng and destination_id!=@start ")[['network_cost', 'destination_id']].reset_index(
            drop=True)
        traversed_latlng.append(start)
        distance_op += temp_min[['network_cost']].min()[0]
        start = temp_min.iloc[temp_min[['network_cost']].idxmin()[0], 1]
        optimized_route.append(start)


    final_df = pd.DataFrame(
        {'optimized_route': optimized_route, 'optimized_distance': np.nan})
    final_df.loc[0, 'optimized_distance'] = distance_op
    final_df = final_df[['optimized_route','optimized_distance']]
    final_df=final_df.merge(geo_coordinates,left_on='optimized_route',right_on='id')[['optimized_distance','latitude', 'longitude']]
    final_df.to_csv(f'/Users/muhammadabdul/Desktop/Work/route_optimization/new_attempt/optimized_route.csv')

    return final_df

def shortest_path(optimized_df):
    for i in range(1,len(optimized_df)):
        start_point=str(optimized_df.iloc[i-1,2]) + ',' + str(optimized_df.iloc[i-1,1])
        end_point = str(optimized_df.iloc[i, 2]) + ',' + str(optimized_df.iloc[i, 1])
        processing.run("qneat3:shortestpathpointtopoint",
                       {'INPUT': '/Users/muhammadabdul/Desktop/Work/NTRC_Lahore-Road-Network/Lahore_District.shp',
                        'START_POINT': f'{start_point}',
                        'END_POINT': f'{end_point}', 'STRATEGY': 0, 'ENTRY_COST_CALCULATION_METHOD': 0,
                        'DIRECTION_FIELD': 'direction', 'VALUE_FORWARD': '1', 'VALUE_BACKWARD': '1', 'VALUE_BOTH': '0',
                        'DEFAULT_DIRECTION': 2, 'SPEED_FIELD': '', 'DEFAULT_SPEED': 5, 'TOLERANCE': 0,
                        'OUTPUT': f'/Users/muhammadabdul/Desktop/Work/route_optimization/new_attempt/layer_files/{i-1}-{i}.gpkg'})

        temp_layer_path=f'/Users/muhammadabdul/Desktop/Work/route_optimization/new_attempt/layer_files/{i-1}-{i}.gpkg'

        temp_layer=QgsVectorLayer(temp_layer_path, f"{i-1}-{i}.gpkg", "ogr")
        QgsProject.instance().addMapLayer(temp_layer)

        symbol = QgsLineSymbol.createSimple({  'width': 1.26})
        temp_layer.renderer().setSymbol(symbol)

def take_picture(extent):
    canvas = iface.mapCanvas()
    project = QgsProject.instance()
    manager = project.layoutManager()
    home_path = '/Users/muhammadabdul/Desktop/Work/route_optimization/new_attempt/'

    x_min = extent.xMinimum()
    y_min = extent.yMinimum()
    x_max = extent.xMaximum()
    y_max = extent.yMaximum()

    extent = QgsRectangle(x_min,y_min,x_max,y_max)

    layouts_list = manager.printLayouts()
    for layout in layouts_list:
        if layout.name() == "Layout":
            manager.removeLayout(layout)

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("Layout")
    manager.addLayout(layout)

    # create map item in the layout
    map = QgsLayoutItemMap(layout)
    map.setRect(0, 0, 20, 20)

    map.zoomToExtent((extent))

    map.attemptResize(QgsLayoutSize(295, 210, QgsUnitTypes.LayoutMillimeters))
    map.setBackgroundColor(QColor(255, 255, 255, 0))
    layout.addLayoutItem(map)

    layout = manager.layoutByName("Layout")
    exporter = QgsLayoutExporter(layout)

    image_name = "output_img.png"
    image_path = os.path.join(home_path, image_name)

    settings = QgsLayoutExporter.ImageExportSettings()
    exporter.exportToImage(image_path, settings)

df_destinations = pd.read_csv('/Users/muhammadabdul/Desktop/Work/route_optimization/new_attempt/destinations.csv')

df_destinations['id'] = df_destinations.index

total_destinations = df_destinations.shape[0]

add_raster()

df_OD = OD_matrix()

optimized_df = optimized_df(df_OD,total_destinations,df_destinations)

shortest_path(optimized_df)

extent = add_points()

take_picture(extent)




