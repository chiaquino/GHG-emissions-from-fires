"""
@Author: Chiara Aquino
@Date : 12 January 2024

Functions to calculate GHG emissions using model from Chiriacò et al.(2013)
"""

def get_effis_data(path_to_effis_data,**kwargs):

    """
    Retrieve data from the EFFIS shapefile and filter it based on selected columns and values.

    Parameters:
    - path_to_effis_data (string) : location of the EFFIS shapefile, as downloaded from https://effis.jrc.ec.europa.eu/applications/data-and-services 
    - *kwargs: Optional arguments for column name and corresponding values.

    Returns:
    - pd.DataFrame: Filtered DataFrame.
    """
    import geopandas
    import pandas as pd

    #open EFFIS shapefile
    df = geopandas.read_file(path_to_effis_data)
    
    #Copy the original DataFrame
    filtered_df = df.copy()

    #extract year from EFFIS date column so that the DataFrame can be filtered by year only
    filtered_df['FIREDATE'] = pd.to_datetime(filtered_df['FIREDATE'], format="mixed")
    filtered_df['YEAR'] = filtered_df['FIREDATE'].dt.year
    
    #rename id column to avoid confusion
    filtered_df.rename(columns={'id': 'ID'}, inplace=True)
    
    #filter by selected columns specified in optional arguments
    for column, value in kwargs.items():
        
        # filter only for values that have been declared in function
        if value is not None:
            filtered_df = filtered_df[filtered_df[column] == value]
            
            #Check if the specified value exists in the filtered DataFrame
            if filtered_df.empty:
                raise ValueError(f"No data found where '{column}' is '{value}'.")
    
    return filtered_df


def get_total_burnt_area(df,forest_types):
    """
    Calculate burnt area from dataframe for each forest class

    Parameters:
    - df (pd.DataFrame): input DataFrame containing burnt area for each fire event 
    - forest_types (list of str): forest classes 

    Returns:
    -  pd.DataFrame: Processed DataFrame containing total burnt area in Ha for each forest class
    """
       
    # Burnt areas in EFFIS for each forest class are reported in percentage units
    # To get areas for each burnt forest type in Ha, we need to 
    # multiply the proportion of each burnt forest type by total burnt area in Ha
    for type in forest_types: 
        df[type+'_AREA_HA'] = df[type].astype(float)/ 100 * df['AREA_HA'].astype(float) 
    
    # Retain in DataFrame only columns with burnt areas in hectares for each forest type
    df_areas_by_forest_type = df.filter(regex='_AREA_HA')

    # Get TOTAL burnt areas in hectares for each forest type by summing over each column
    df_sum_areas_by_forest_type = df_areas_by_forest_type.astype(float).sum(axis=0)
    
    return df_sum_areas_by_forest_type
    
def get_biomass(path_to_biomass_lookup_table, region=None):
    """
    Retrieve pre disturbance biomass for each vegetation type
    Data is derived from average standing volume estimates from National Forest Inventory 2015 (INFC2015). INFC2015 classes have been 
    averaged for each of the 20 Italian administrative regions to match EFFIS vegetation classes

    Parameters:
    - path_to_biomass_lookup_table (str) : location of Effis - National Forest Inventory 2015 lookup table
    - region (str): Italian region of interest. Default region is None. 
    
    Returns:
    - pd.DataFrame: Processed DataFrame with average biomass values per selected region per vegetation type
    """
    import pandas as pd

    # get EFFIS-INFC2015 biomass table
    effis_INFC2015 = pd.read_csv(path_to_biomass_lookup_table)
    
    #if region is specified, then select row containing values for that region
    if region is not None:
        effis_INFC2015_biomass_by_region = effis_INFC2015[effis_INFC2015['Region'] == region]
    
    # if region is not specified (if region left as None) get average values for Italy
    else:
        effis_INFC2015_biomass_by_region = effis_INFC2015[effis_INFC2015['Region'] == "Italia"]
        
    return effis_INFC2015_biomass_by_region


def get_combustion_factor(path_to_effis_bovio_table,path_to_fire_damage_table,scorch_height=None):
    """
    Retrieve combustion factor for each forest type.
    These value are retrieved from Table 4 and Table 5 in Chiriacò et al.(2013), in turn taken from Bovio et al.(2007) 
    where vegetation classes need to be matched to EFFIS forest types.

    Parameters:
    - path_to_effis_bovio_table (str) : location of lookup table matching vegetation classes in Table 4 (Chiriacò et al.,2013) with EFFIS vegetation classes
    - path_to_fire_damage_table (str) : location of scorch height table, corresponding to Table 5 (Chiriacò et al.,2013)
    - scorch_height (int): height of the flame, as specified by the user. Default is None.

    Returns:
    - pd.DataFrame: Processed DataFrame with combustion factor values per vegetation type
    """
    import pandas as pd
    
    #read in table with conversion between EFFIS forest types-BOVIO vegetation classes 
    effis_bovio_df= pd.read_csv(path_to_effis_bovio_table)
    #read in table with fire damage values
    fire_damage_df= pd.read_csv(path_to_fire_damage_table)

    #Merge the two tables, to match EFFIS forest types to fire_damage table
    merged = pd.merge(effis_bovio_df, fire_damage_df, on= "BOVIO_CLASS")

    #drop Bovio vegetation classes and eliminate duplicates
    merged = merged.drop(['BOVIO_NAME','BOVIO_CLASS'], axis=1).drop_duplicates().sort_values(by='EFFIS_CLASS')

    #group by EFFIS forest class and calculate average of fire damage values for each EFFIS forest class
    grouped = merged.groupby(['EFFIS_CLASS']).mean().reset_index()

    #Now from this table, select the fire damage value that correspond to the scorch height 
    
    #if scorch height values are not specified (scorch_height = None) take average of the highest two fire damage classes
    if scorch_height is None:
        grouped['COMBUSTION_FACTOR']  = grouped[['3.5-4.5', '>4.5']].mean(axis=1)
    
    # if they are specified, match scorch height values with its corresponding fire damage column
    else:
        if scorch_height < 1:
            grouped['COMBUSTION_FACTOR']  = grouped['<1']
        elif 1 <= scorch_height < 2.5:
            grouped['COMBUSTION_FACTOR']  = grouped['1-2.5']
        elif 2.5 <= scorch_height < 3.5:
            grouped['COMBUSTION_FACTOR']  = grouped['2.5-3.5']
        elif 3.5 <= scorch_height < 4.5:
            grouped['COMBUSTION_FACTOR']  = grouped['3.5-4.5']
        else:
            grouped['COMBUSTION_FACTOR']  = grouped['>4.5']

    #select only forest classes and combustion factor for the specified scorch height
    grouped = grouped[['EFFIS_CLASS','COMBUSTION_FACTOR']]

    # Set the vegetation class column as the index, then tidy up table so that it contains only fire damage and forest classes
    combustion_factor_df = grouped.set_index('EFFIS_CLASS').T.astype(object)
    combustion_factor_df = combustion_factor_df.reset_index(level=0, drop=True)
    combustion_factor_df = combustion_factor_df.rename_axis(None, axis=1)

    return combustion_factor_df

def get_total_annual_GHG_emissions(A,B,C,path_to_emission_factors_table,forest_types):
    """

    This function puts together all the previous steps of the model and calculates final GHG emissions. 
    
    Parameters: 
    - A (pd.DataFrame) : burnt area for each forest class, as retrieved by function get_total_burnt_area()
    - B (pd.DataFrame) : pre disturbance biomass for each vegetation type, as retrived by function get_biomass()
    - C (pd.DataFrame) : combustion factor for each forest type, as retrieved by function get_combustion_factor()
    - path_to_emission_factors_table (str) : location of table containing GHG emission values (as from IPCC2003)
    - forest_types (list of str) : forest classes 

    Returns:
    - Float: Total GHG emissions
    """
    import pandas as pd
    import numpy as np
    
    #### CALCULATE MODEL PARAMETERS #######
    
    # Multiply A X B
    # Create empty dataframe to calculate AGB (Above ground biomass) of burnt area
    df_totC_INF2015 = pd.DataFrame()

    # Calculate AGB of burnt area for each forest type. Multiply x 1e3 to convert AGB values from Mg to Kg
    for forest_type in forest_types:
        df_totC_INF2015[forest_type] = A[forest_type+"_AREA_HA"] * B[forest_type].astype(float) * 1000

    # Multiply AB x C
    # Create empty dataframe to calculate combustion factor for each burnt AGB in ha
    df_totC_INF2015_combustion_factor = pd.DataFrame()

    # Calculate combustion factor for each burnt AGB per ha for each forest type.
    for forest_type in forest_types:
        df_totC_INF2015_combustion_factor[forest_type] = df_totC_INF2015[forest_type] * C[forest_type][0]
    
    # Get emissions for each GHG compound (D)
    # Read table with emission factors for each GHG compound
    df_emission_factors = pd.read_csv(path_to_emission_factors_table)

    #convert Dataframes to array to perform pair-wise multiplication between GHG values and forest types
    array_df_totC_INF2015_combustion_factor = df_totC_INF2015_combustion_factor.to_numpy()
    array_df_emission_factors = df_emission_factors.to_numpy()

    # Perform element-wise multiplication between forest types and GHG emission factors
    result_array = np.multiply.outer(array_df_emission_factors, array_df_totC_INF2015_combustion_factor)
    
    #convert resulting array into Dataframe, and rename columns using forest types
    df_ghg = pd.DataFrame(result_array.reshape(array_df_emission_factors.shape[1], array_df_totC_INF2015_combustion_factor.shape[1]), columns=df_totC_INF2015_combustion_factor.columns)

    #rename rows with names of GHG emission factors
    df_ghg.index = df_emission_factors.columns.values.tolist()
    
    #multiply all factors by 10^(-6) to get emission factors into units of kgtons
    df_ghg_kton = df_ghg * 1e-6

    #convert CH4 and N2O in GWP units CO2 equivalent
    df_ghg_kton.loc['CH4'] =  df_ghg_kton.loc['CH4'] * 28
    df_ghg_kton.loc['N2O'] =  df_ghg_kton.loc['N2O'] * 273
    
    #select only relevant GHG compounds (exclude precursors)
    ghg_co2eq_columns = ['CO2', 'CH4', 'N2O']
    
    # sum GHG by forest types
    emissions_by_forest_type_co2eq = df_ghg_kton.loc[ghg_co2eq_columns, :].sum()
    
    # sum over ALL forest types to get final GHG per burnt area
    total_emissions_co2eq = emissions_by_forest_type_co2eq.sum()
    
    return total_emissions_co2eq