This package identifies UK postcodes that are within given distances of given
UK postcodes. Those distances are in minutes by car, using OpenStreetMaps for
the routing. See search_parameters.py for information on how to set up the
search. The results will be saved as a pandas dataframe. A jupyter notebook
to view that dataframe of postcodes is provided and this can be inspected then,
e.g., sort by column etc. 

TODO:
- Refine search to full postcodes, not just the outcodes (first part)
- include some visualisation using geopandas or so in the notebook
