import pandas as pd
import pickle
import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options


# define function that finds the distance between two points;
# this distance is in minutes by car, found using OpenStreetMaps routing
def get_distance(orig_lat, orig_lon, dest_lat, dest_lon):
    #  plug in origin/destination latitude/longitude into the url template
    urlpage = url_templ.format(orig_lat, orig_lon, dest_lat, dest_lon)
    # uncomment the following command to see the used urls in the terminal
    # print(urlpage)
    driver.get(urlpage)
    # wait to give browser time to load content
    time.sleep(2)
    # extract cell containing the travel time from the routing summary
    x = driver.find_elements_by_xpath("//*[@id='routing_summary']")
    if len(x) == 0:
        # if routing summary not found, return -1 as travel time
        ret_value = -1
    else:
        # otherwise, extract travel time and return
        y = x[0].text  # string containing time at the end in the format h:mm
        z = y.split(' ')[-1].rstrip('.').split(':')
        ret_value = int(z[0])*60 + int(z[1])
    return ret_value


# set options to use headless browser
options = Options()
options.headless = True

# read in the full list of UK postcodes
pc_raw = pd.read_csv('postcode-outcodes.csv',
                     index_col='postcode', header=0).drop(columns=['id'])

# execute the file with parameters for the search -- those parameters are:
# search area, destinations, url template
min_lat, min_lon, max_lat, max_lon = (None,)*4
destination_distances = None
url_templ = None
output_fname = None
sp_file = open('search_parameters.py', 'r')
exec(sp_file.read())
sp_file.close()

# define list of destinations and dictionary with their coordinates
destinations = list(destination_distances.keys())
destination_coordinates = {}
for x in destinations:
    destination_coordinates[x] = (pc_raw.loc[x, 'latitude'],
                                  pc_raw.loc[x, 'longitude'])

# restrict to postcodes in the given area;
# add columns for distances to destinations
pc = pc_raw[pc_raw.latitude.ge(min_lat)
            & pc_raw.longitude.ge(min_lon)
            & pc_raw.latitude.le(max_lat)
            & pc_raw.longitude.le(max_lon)] \
            .reindex(columns=list(pc_raw.columns)+destinations)
del pc_raw
print('Number of postcodes within given area:', len(pc))
print('Now loop over postcodes and determine distances ...')

# fill in the destination columns
driver = webdriver.Firefox(firefox_options=options)  # headless browser session
for d in destinations:
    print('Destination:', d)
    progress = 0
    dest_coord = destination_coordinates[d]
    dest_lat = dest_coord[0]
    dest_lon = dest_coord[1]
    for p in list(pc.index):
        orig_lat = pc.at[p, 'latitude']
        orig_lon = pc.at[p, 'longitude']
        t = get_distance(orig_lat, orig_lon, dest_lat, dest_lon)
        pc.loc[p, d] = t
        progress += 1
        print(progress, '\t', p, '\t Time:', t)
    pc = pc[pc[d].le(destination_distances[d])]
driver.quit()  # close the headless browser session

# remove postcodes that do not satisfy distance requirements in the last column
d = list(pc.columns)[-1]
pc = pc[pc[d].le(destination_distances[d])]
print('... Done')
print('Number of postcodes satisfying distance requirements:', len(pc))

# save dataframe of postcodes
pc_file = open(output_fname, 'wb')
pickle.dump(pc, pc_file)
pc_file.close()
print('Saved dataframe as "' + output_fname + '"')
