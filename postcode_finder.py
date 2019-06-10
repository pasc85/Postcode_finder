import pandas as pd
import numpy as np
import time
import pickle
import math
import tkinter as tk
import tkinter.scrolledtext as tkst
from selenium import webdriver
import geopandas
from shapely.geometry import Point
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import pyplot as plt


class SearchAreaError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class PostcodeFinder():

    def __init__(self, destination_distances):
        '''Set up the search for postcodes.'''
        # dictionary of destination distances
        self.destination_distances = destination_distances
        self.url_templ = 'https://www.openstreetmap.org/directions?engine=fo' \
                         + 'ssgis_osrm_car&route={:.4f}%2C{:.4f}%3B{:.4f}%2C' \
                         + '{:.4f}#map=5/55.781/-5.962'
        # list of destinations and dictionary with their coordinates
        self.destinations = list(self.destination_distances.keys())
        self.destination_coordinates = {}
        for x in self.destinations:
            self.destination_coordinates[x] = (pc_raw.loc[x, 'latitude'],
                                               pc_raw.loc[x, 'longitude'])
        # set the boundaries for the search,
        # format of search_boundaries: min_lat, min_lon, max_lat, max_lon
        self.search_boundaries = None
        self.set_boundaries()
        sb = self.search_boundaries
        # restrict raw dataframe of postcodes to the search area
        self.pc = pc_raw[pc_raw.latitude.ge(sb[0])
                         & pc_raw.longitude.ge(sb[1])
                         & pc_raw.latitude.le(sb[2])
                         & pc_raw.longitude.le(sb[3])]
        temp_col_list = list(pc_raw.columns) + self.destinations
        # add columns for distances to destinations,
        # those distances will be computed in in pcf_main()
        self.pc = self.pc.reindex(columns=temp_col_list)
        print('Number of postcodes within given area:', len(self.pc))

    def set_boundaries(self):
        '''Set the boundaries for the search.'''

        def min_max_lat_lon(dest):
            '''Return frame around given destination.'''
            v = max_speed  # maximum speed in km per minute
            lat = self.destination_coordinates[dest][0]
            lon = self.destination_coordinates[dest][1]
            dist = v * self.destination_distances[dest]
            delta_lat = PostcodeFinder.compute_delta(lat, lon, dist, 'lat')
            delta_lon = PostcodeFinder.compute_delta(lat, lon, dist, 'lon')
            return (lat-delta_lat, lon-delta_lon, lat+delta_lat, lon+delta_lon)

        # each row of the matrix m corresponds to a destination and contains
        # the search boundaries for that destination, which depends on the
        # entered distance
        m = np.zeros((len(self.destinations), 4))
        for k in range(len(self.destinations)):
            m[k] = min_max_lat_lon(self.destinations[k])
        # take intersection of the frames around individual destinations
        sb = (max(m[:, 0]), max(m[:, 1]), min(m[:, 2]), min(m[:, 3]))
        # raise error if search area is empty (recall
        # format of search_boundaries: min_lat, min_lon, max_lat, max_lon)
        if sb[0] > sb[2] or sb[1] > sb[3]:
            raise SearchAreaError('Empty search area. Make distances bigger.')
        # set search boundaries and print in terminal
        self.search_boundaries = sb
        print('Search area:')
        print('Latitude : ', (sb[0], sb[2]))
        print('Longitude: ', (sb[1], sb[3]))

    def pcf_main(self):
        '''Computes distances for the destination columns.'''
        # headless browser session to query OpenStreetMaps routing
        options = webdriver.firefox.options.Options()
        options.headless = True
        driver = webdriver.Firefox(firefox_options=options)
        # loop over columns, i.e. destination postcodes
        print('Loop over destination postcodes and determine distances ...')
        for d in self.destinations:
            print('Destination:', d)  # TODO also print number of pc
            progress = 0
            dest_coord = self.destination_coordinates[d]
            dest_lat = dest_coord[0]
            dest_lon = dest_coord[1]
            # loop over rows, i.e. origin postcodes
            for p in list(self.pc.index):
                orig_lat = self.pc.at[p, 'latitude']
                orig_lon = self.pc.at[p, 'longitude']
                t = self.get_distance(orig_lat, orig_lon,
                                      dest_lat, dest_lon, driver)
                self.pc.loc[p, d] = t
                progress += 1
                print(progress, '\t', p, '\t Time:', t)
            # remove postcodes that don't satisfy the distance requirement
            # for the destination that has just been computed
            self.pc = self.pc[self.pc[d].le(self.destination_distances[d])]
            self.pc = self.pc.astype({d: int})
        driver.quit()  # close the headless browser session
        # remove postcodes that don't satisfy distance requ in the last column
        d = list(self.pc.columns)[-1]
        self.pc = self.pc[self.pc[d].le(self.destination_distances[d])]
        print('... Done')
        print('Number of postcodes satisfying distance requirements:',
              len(self.pc))

    def get_distance(self, orig_lat, orig_lon, dest_lat, dest_lon, driver):
        '''Find driving distance between two points using OSM routing.'''
        # URL to be requested
        urlpage = self.url_templ.format(orig_lat, orig_lon, dest_lat, dest_lon)
        driver.get(urlpage)
        time.sleep(wait_time)  # wait to give browser time to load content
        # extract cell containing the travel time from the routing summary
        x = driver.find_elements_by_xpath("//*[@id='routing_summary']")
        if len(x) == 0:
            # if 'routing summary' not found, return -1 as travel time
            ret_value = -1
        else:
            # otherwise, extract travel time and return
            y = x[0].text  # string containing time in the format h:mm
            z = y.split(' ')[-1].rstrip('.').split(':')
            ret_value = int(z[0])*60 + int(z[1])
        return ret_value

    def compute_delta(lat, lon, dist, direction):
        '''Compute coordinate difference corresponding to given distance.'''
        R = 6371
        t = (math.tan(dist/R/2))**2
        c = 1
        if direction == 'lon':
            lat_rad = lat*math.pi/180
            c = (math.cos(lat_rad))**2
        d_rad = 2*math.asin(math.sqrt(t/(1+t)/c))
        return d_rad*180/math.pi

    def compute_distance(a_lat, a_lon, b_lat, b_lon):
        '''Compute distance between two points given by coordinates.'''
        R = 6371
        c = math.pi/180
        a_lat = a_lat * c
        a_lon = a_lon * c
        b_lat = b_lat * c
        b_lon = b_lon * c
        d_lat = b_lat - a_lat
        d_lon = b_lon - a_lon
        a = (math.sin(d_lat/2))**2 \
            + math.cos(b_lat) * math.cos(a_lat) * (math.sin(d_lon/2))**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def get_pc_as_df(self):
        '''Return table of postcodes as pandas dataframe.'''
        return self.pc

    def get_pc_as_str(self):
        '''Return table of postcodes as string.'''
        return self.pc.to_string()


class PostcodeVisualiser():

    def __init__(self, pcf):
        self.pcf = pcf
        self.vis_boundaries = None
        self.pc_centres = None
        self.dest_coords = None
        self.set_dest_coords()
        self.set_vis_boundaries()
        self.set_pc_centres()
        self.background_map = geopandas.read_file('postcode_shapes'
                                                  + '/Distribution/Areas.shp')
        self.pc_shapes = geopandas.read_file('postcode_shapes'
                                             + '/Distribution/Districts.shp') \
                                  .rename(columns={'name': 'postcode'}) \
                                  .set_index('postcode') \
                                  .reindex(index=self.pcf.pc.index)

    def set_vis_boundaries(self):

        def make_square(x):
            return_value = None
            centre_lat = (x[0]+x[2])/2
            centre_lon = (x[1]+x[3])/2
            north_south = PostcodeFinder.compute_distance(x[0], centre_lon,
                                                          x[2], centre_lon)
            east_west = PostcodeFinder.compute_distance(centre_lat, x[1],
                                                        centre_lat, x[3])
            if north_south > east_west:
                delta = PostcodeFinder.compute_delta(centre_lat, centre_lon,
                                                     north_south/2, 'lon')
                return_value = (x[0], centre_lon-delta, x[2], centre_lon+delta)
            else:
                delta = PostcodeFinder.compute_delta(centre_lat, centre_lon,
                                                     east_west/2, 'lat')
                return_value = (centre_lat-delta, x[1], centre_lat+delta, x[3])
            return return_value

        sb = self.pcf.search_boundaries
        vb = (min(sb[0], min(self.dest_coords.latitude)),
              min(sb[1], min(self.dest_coords.longitude)),
              max(sb[2], max(self.dest_coords.latitude)),
              max(sb[3], max(self.dest_coords.longitude)))
        self.vis_boundaries = make_square(vb)

    def set_pc_centres(self):
        temp_df = self.pcf.pc.reindex(columns=['latitude', 'longitude',
                                               'coordinates'])
        temp_df['coordinates'] = list(zip(temp_df.longitude, temp_df.latitude))
        temp_df['coordinates'] = temp_df['coordinates'].apply(Point)
        self.pc_centres = geopandas.GeoDataFrame(temp_df,
                                                 geometry='coordinates')

    def set_dest_coords(self):
        cols = list(self.pcf.pc.columns)
        cols.remove('longitude')
        cols.remove('latitude')
        temp_df = pc_raw.reindex(index=cols)
        temp_df['coordinates'] = list(zip(temp_df.longitude, temp_df.latitude))
        temp_df['coordinates'] = temp_df['coordinates'].apply(Point)
        self.dest_coords = geopandas.GeoDataFrame(temp_df,
                                                  geometry='coordinates')

    def vis_main(self):
        fig, axs = plt.subplots(1, figsize=figure_size, dpi=100)
        self.background_map.plot(ax=axs, color='green', edgecolor='black')
        self.pc_shapes.plot(ax=axs, color='yellow', edgecolor='red')
        if draw_search_area:
            sb = self.pcf.search_boundaries
            rect = Rectangle((sb[1], sb[0]), sb[3]-sb[1], sb[2]-sb[0],
                             linestyle='--', fill=False,
                             linewidth=1, color='b')
            axs.add_patch(rect)
        if pc_labels:
            props = dict(boxstyle='round', facecolor='linen', alpha=1)
            for p in self.pc_centres.iterrows():
                axs.text(p[1]['longitude'], p[1]['latitude'], p[0],
                         horizontalalignment='center', fontsize=11, bbox=props)
        self.dest_coords.plot(ax=axs, color='blue', markersize=40)
        vb = self.vis_boundaries
        axs.set_xlim(([vb[1], vb[3]]))
        axs.set_ylim(([vb[0], vb[2]]))
        axs.set_aspect('auto')
        return fig, axs


class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.pack()
        self.create_widgets()

    def create_widgets(self):

        self.info_label = tk.Label(self)
        self.info_label['text'] = 'Enter destination postcode ' \
                                  + 'and maximum distance'
        self.info_label.grid(row=0, column=0, columnspan=4)

        self.dest1_label = tk.Label(self, text='Destination 1: ')
        self.dest1_label.grid(row=1, column=0)
        self.dest2_label = tk.Label(self, text='Destination 2: ')
        self.dest2_label.grid(row=2, column=0)
        self.dest3_label = tk.Label(self, text='Destination 3: ')
        self.dest3_label.grid(row=3, column=0)

        self.dest1_pc_entry = tk.Entry(self, width=4)
        self.dest1_pc_entry.grid(row=1, column=1)
        self.dest2_pc_entry = tk.Entry(self, width=4)
        self.dest2_pc_entry.grid(row=2, column=1)
        self.dest3_pc_entry = tk.Entry(self, width=4)
        self.dest3_pc_entry.grid(row=3, column=1)

        self.dest1_dist_entry = tk.Entry(self, width=3)
        self.dest1_dist_entry.grid(row=1, column=2)
        self.dest2_dist_entry = tk.Entry(self, width=3)
        self.dest2_dist_entry.grid(row=2, column=2)
        self.dest3_dist_entry = tk.Entry(self, width=3)
        self.dest3_dist_entry.grid(row=3, column=2)

        self.dest_err_label = tk.Label(self, fg='red')
        self.dest_err_label.grid(row=5, column=3)

        self.sample_search_button = tk.Button(self)
        self.sample_search_button['text'] = 'Sample search'
        self.sample_search_button['command'] = self.enter_sample
        self.sample_search_button.grid(row=4, column=0)

        self.clear_button = tk.Button(self)
        self.clear_button['text'] = 'Clear'
        self.clear_button['command'] = self.clear_all
        self.clear_button.grid(row=4, column=3, ipadx=28)

        self.find_postcodes_button = tk.Button(self)
        self.find_postcodes_button['text'] = 'Find postcodes'
        self.find_postcodes_button['command'] = self.app_main
        self.find_postcodes_button.grid(row=6, column=3, padx=10)

        self.save_label = tk.Label(self, text='Save dataframe as ')
        self.save_label.grid(row=5, column=0, sticky=tk.E)
        self.save_entry = tk.Entry(self, width=8)
        self.save_entry.grid(row=5, column=1, columnspan=2, sticky=tk.W)

        self.visualisation_label = tk.Label(self, text='Draw map')
        self.visualisation_label.grid(row=6, column=0, sticky=tk.E)
        self.visualisation_CB = tk.Checkbutton(self)
        self.visualisation_CB_value = tk.IntVar()
        self.visualisation_CB['variable'] = self.visualisation_CB_value
        self.visualisation_CB.grid(row=6, column=1, sticky=tk.W)

        self.output_ST = tkst.ScrolledText(self, width=48)
        self.output_ST.grid(row=7, column=0, rowspan=4, columnspan=4)

    def app_main(self):
        self.clear_error()
        self.output_ST.delete(1.0, tk.END)
        if not self.valid_filename():
            self.dest_err_label['text'] = 'invalid filename'
            return
        input_dict = {}
        input_dict[self.dest1_pc_entry.get().strip()] \
            = self.dest1_dist_entry.get().strip()
        input_dict[self.dest2_pc_entry.get().strip()] \
            = self.dest2_dist_entry.get().strip()
        input_dict[self.dest3_pc_entry.get().strip()] \
            = self.dest3_dist_entry.get().strip()
        input_dict[''] = ''
        del input_dict['']
        if len(input_dict) == 0:
            self.dest_err_label['text'] = 'enter destination(s)'
            return
        if not set(input_dict.keys()).issubset(pc_set):
            self.dest_err_label['text'] = 'invalid postcode(s)'
            return
        try:
            for x in input_dict.keys():
                input_dict[x] = int(input_dict[x])
        except ValueError:
            self.dest_err_label['text'] = 'invalid distance(s)'
            return
        if min(input_dict.values()) <= 0:
            self.dest_err_label['text'] = 'invalid distance(s)'
            return
        try:
            pcf = PostcodeFinder(input_dict)
        except SearchAreaError as sae:
            print(sae)
            self.dest_err_label['text'] = 'empty search area'
            return
        pcf.pcf_main()
        output_fname = self.save_entry.get().strip()
        if output_fname:
            pc_file = open(output_fname, 'wb')
            pickle.dump(pcf.get_pc_as_df(), pc_file)
            pc_file.close()
            print('Saved dataframe as "' + output_fname + '"')
        self.output_ST.insert(1.0, pcf.get_pc_as_str())
        if self.visualisation_CB_value.get() == 1 and len(pcf.pc) > 0:
            vis_window = tk.Tk()
            vis_window.title('Postcodes satisfying the distance requirements')
            pcv = PostcodeVisualiser(pcf)
            fig, axs = pcv.vis_main()
            vis_canvas = FigureCanvasTkAgg(fig, master=vis_window)
            vis_canvas.draw()
            vis_canvas.get_tk_widget().pack()
            vis_window.mainloop()

    def clear_error(self):
        self.dest_err_label['text'] = ''

    def clear_all(self):
        self.clear_error()
        self.dest1_pc_entry.delete(0, tk.END)
        self.dest2_pc_entry.delete(0, tk.END)
        self.dest3_pc_entry.delete(0, tk.END)
        self.dest1_dist_entry.delete(0, tk.END)
        self.dest2_dist_entry.delete(0, tk.END)
        self.dest3_dist_entry.delete(0, tk.END)
        self.output_ST.delete(1.0, tk.END)

    def enter_sample(self):
        self.clear_all()
        self.dest1_pc_entry.insert(0, 'EX1')
        self.dest2_pc_entry.insert(0, 'TA1')
        self.dest1_dist_entry.insert(0, 40)
        self.dest2_dist_entry.insert(0, 35)

    def valid_filename(self):
        output_fname = self.save_entry.get().strip()
        if output_fname == '':
            return True
        for c in output_fname:
            if not any([c.isalpha(), c.isdigit(), c == '_',
                        c == '-', c == '.']):
                return False
        return True


# table of all UK postcodes with coordinates
pc_raw = pd.read_csv('postcode-outcodes.csv',
                     index_col='postcode', header=0).drop(columns=['id'])
pc_set = set(pc_raw.index)  # set of valid UK postcodes

# other constants
draw_search_area = True  # to check automatic choice of search area
figure_size = (6, 6)  # figure size for the geopandas visualisation
max_speed = 1.2
# TODO: include max_speed in GUI and introduce SPY button
wait_time = 2  # allow time for query, see get_distance()
pc_labels = False  # labels for postcodes on geopandas map

# start the application
root = tk.Tk()
root.title('Postcode Finder by PP')
app = Application(master=root)
app.mainloop()
