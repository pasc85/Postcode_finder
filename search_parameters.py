# minimum/maximum latitude/longitude for the area to search
min_lat = 50.6
max_lat = 51.1
min_lon = -3.6
max_lon = -3.0

# dictionary of destinations, for example: running the script with
# destination_distances = {'EX1': 45, 'TA1': 45}
# produces a dataframe of all postcodes within the area described above that
# are within 45 minutes (by car) of both EX1 (Exeter) and TA1 (Taunton)
destination_distances = {'EX1': 40, 'TA1': 35}

# template for the url which does the routing,
# plug in latitude/longitude of origin/destination later
url_templ = 'https://www.openstreetmap.org/directions?engine=fossgis_osrm_car'\
            + '&route={:.4f}%2C{:.4f}%3B{:.4f}%2C{:.4f}#map=5/55.781/-5.962'

# name of the pickle file in which output dataframe will be saved
output_fname = 'pc.p'

# Notes:
# - geckodriver needs to be installed
# - if a distance -1 is obtained, it means that the browser wasn't able to
#   scrape the travel time for that entry --> try to give it more time
#   via the command time.sleep(..) in find_postcodes.py
