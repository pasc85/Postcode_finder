This package identifies UK postcodes that are within prescribed driving
distances of given UK postcodes. Those driving distances are found using
OpenStreetMaps routing. The resulting table is displayed as text in the
application and can also be saved as a pandas dataframe or be displayed
as a geopandas map.

The settings below the output box are more advanced and the best thing to
do to get a first idea of how the application works would be to try the basic
sample search without changing any of the advanced settings.

Author: Pascal Philipp

Source of the postcode data: 
The table of postcodes that is used is downloaded from
https://www.freemaptools.com/download-uk-postcode-lat-lng.htm

Requirements:
- geckodriver needs to be installed
- recreate python environment using 'environment.yml'
- for the geopandas visualisation, the shapefiles under 
'UK postcode boundary polygons' on the page
https://www.opendoorlogistics.com/downloads/
need to be downloaded and put in folder a folder caller 'postcode_shapes'
in the working directory.

Demo:
https://www.youtube.com/watch?v=jSgu0_SoSNo
