# -*- coding: utf-8 -*-
"""
@author: Chiara Aquino

@date: 12 January 2024

This script calculates GHG emissions using the functions defined in
ghg_fire_emissions_functions.py

"""

############################################################################
########################### IMPORT LIBRARIES ################################
############################################################################
from ghg_fire_emissions_functions import *
import numpy as np

##############################################################################
##### LOCATION OF INPUT TABLES ########
##############################################################################
#EFFIS data on burnt area
effis_table = '../data/shapefiles/effis_shapefile_downloaded_6Dec23/modis.ba.poly.shp'
# SERCO data
serco_shapefile = '../data/shapefiles/Serco_S4-08-01/S4-08-01_SARDEGNA_20210722_20210730_BA.shp'

#BIOMASS
INFC15_lookup_table = "../data/tables/INFC15_FOREST_CLASSES_LOOKUP.csv"
biomass_table = "../data/tables/INFC15_AGB_PER_REGION.csv"

#COMBUSTION FACTOR
effis_bovio_conversion_table = "../data/tables/C_FACTOR_BOVIO_FOREST_CLASSES_LOOKUP.csv"
#FIRE DAMAGE
fire_damage_table = "../data/tables/C_FACTOR_BOVIO_SCORCH_HEIGHT.csv"
#EMISSION FACTORS
emission_factors_table = "../data/tables/GHG_EMISSION_FACTORS.csv"

##############################################################################
#################### PARAMETERS OF CHOICE ####################################
##############################################################################
input_data = "EFFIS"
#input_data = "SERCO"
fire_id = None
year = 2021
country = "IT" 
region = "Calabria"
province = "Cosenza"
commune = None
scorch_height = 15
language = "ENGLISH"
#landcover="CLC18"
landcover = "EFFIS"
crs = "epsg:4326"


##############################################################################
#################### GHG CALCULATION ####################################
##############################################################################

# STEP 1. Get total burnt area (A) for each vegetation type
# In this example, we are choosing EFFIS data. First, we need to filter EFFIS by selecting columns corresponding to our chosen parameters
burnt_shape = import_data(input_data,effis_shapefile,ID=fire_id,YEAR=year,COUNTRY=country,PROVINCE=province,COMMUNE=commune)
#burnt_shape = import_data(input_data,serco_shapefile)

#get total burnt area for each fire event, organised by forest classes
A = get_total_burnt_area(landcover,clc18_shapefile, burnt_shape, forest_classes, crs)

# STEP 2. Get biomass of available fuel (B) for each vegetation type
B = get_biomass(INFC15_lookup_table, biomass_table, landcover, region)

# STEP 3. Get combustion factor (C) for each vegetation type
C = get_combustion_factor(c_factor_bovio_conversion_table,fire_damage_table,landcover,scorch_height)

# STEP 4. Calculate total GHG emissions from emission factors
ghg, emissions_by_forest_type_co2eq = get_total_annual_GHG_emissions(A,B,C,emission_factors_table,forest_classes)

#check Total GHG per year
print("total GHG emissions for the year " + str(year)  +" in " + str(province) +" province: " + str(np.round(ghg,2))+ " Kton CO2eq")

area = A.copy()
ghg_per_ha = ghg/area
print("GHG per ha:",ghg_per_ha)

#burnt_shape_output="../outputs/Oristano21/effis_ba_oristano21.shp"
#ghg_by_lc_output ="../outputs/Oristano21/ghg_by_forest_class_oristano21.shp"
#plot_burnt_area_and_clc18_classes(landcover_legend_table,language,burnt_shape,emissions_by_forest_type_co2eq)

ghg_table = "../outputs/GHG_from_"+input_data+"_"+landcover+"_"+PROVINCE+"_scorch_height_"+scorch_height+".csv"
save_ghg_emissions(ghg, ghg_table,YEAR=year,COUNTRY=country,REGION=region,PROVINCE=province,COMMUNE=commune)







