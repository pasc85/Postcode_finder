import tkinter as tk
import tkinter.scrolledtext as tkst
import pandas as pd
import time
import pickle
import numpy as np
import math
from selenium import webdriver
from selenium.webdriver.firefox.options import Options


class PostcodeFinder():

    def __init__(self, destination_distances):
        self.destination_distances = destination_distances
        self.url_templ = 'https://www.openstreetmap.org/directions?engine=fos'\
                         + 'sgis_osrm_car&route={:.4f}%2C{:.4f}%3B{:.4f}%2C'\
                         + '{:.4f}#map=5/55.781/-5.962'
        self.destinations = list(self.destination_distances.keys())
        self.destination_coordinates = {}
        for x in self.destinations:
            self.destination_coordinates[x] = (pc_raw.loc[x, 'latitude'],
                                               pc_raw.loc[x, 'longitude'])
        self.search_boundaries = None
        # format of search boundaries: min_lat, min_lon, max_lat, max_lon
        self.set_boundaries()
        sb = self.search_boundaries
        # restrict raw dataframe of postcodes to the search area
        self.pc = pc_raw[pc_raw.latitude.ge(sb[0])
                         & pc_raw.longitude.ge(sb[1])
                         & pc_raw.latitude.le(sb[2])
                         & pc_raw.longitude.le(sb[3])]
        temp_col_list = list(pc_raw.columns) + self.destinations
        # add columns for distances to destinations (to be filled in in main())
        self.pc = self.pc.reindex(columns=temp_col_list)
        print('Number of postcodes within given area:', len(self.pc))

    def set_boundaries(self):
        def min_max_lat_lon(dest):
            v = 1.0  # maximum speed in km per minute
            lat = self.destination_coordinates[dest][0]
            lon = self.destination_coordinates[dest][1]
            dist = v * self.destination_distances[dest]
            delta_lat = PostcodeFinder.compute_delta(lat, lon, dist, 'lat')
            delta_lon = PostcodeFinder.compute_delta(lat, lon, dist, 'lon')
            return (lat-delta_lat, lon-delta_lon, lat+delta_lat, lon+delta_lon)
        m = np.zeros((len(self.destinations), 4))
        for k in range(len(self.destinations)):
            m[k] = min_max_lat_lon(self.destinations[k])
        sb = (max(m[:, 0]), max(m[:, 1]), min(m[:, 2]), min(m[:, 3]))
        self.search_boundaries = sb
        print('Search area:')
        print('Latitude : ', (sb[0], sb[2]))
        print('Longitude: ', (sb[1], sb[3]))

    def main(self):
        print('Loop over destination postcodes and determine distances ...')
        # headless browser session
        options = Options()
        options.headless = True
        driver = webdriver.Firefox(firefox_options=options)
        # fill in distance in each column (i.e. for each destination)
        for d in self.destinations:
            print('Destination:', d)
            progress = 0
            dest_coord = self.destination_coordinates[d]
            dest_lat = dest_coord[0]
            dest_lon = dest_coord[1]
            for p in list(self.pc.index):
                orig_lat = self.pc.at[p, 'latitude']
                orig_lon = self.pc.at[p, 'longitude']
                t = self.get_distance(orig_lat, orig_lon,
                                      dest_lat, dest_lon, driver)
                self.pc.loc[p, d] = t
                progress += 1
                print(progress, '\t', p, '\t Time:', t)
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
        # find distance between two points
        # in minutes by car, using OSM routing:
        urlpage = self.url_templ.format(orig_lat, orig_lon, dest_lat, dest_lon)
        # print(urlpage)
        driver.get(urlpage)  # wait to give browser time to load content
        time.sleep(2)
        # extract cell containing the travel time from the routing summary
        x = driver.find_elements_by_xpath("//*[@id='routing_summary']")
        if len(x) == 0:
            # if routing summary not found, return -1 as travel time
            ret_value = -1
        else:
            # otherwise, extract travel time and return
            y = x[0].text  # string containing time in the format h:mm
            z = y.split(' ')[-1].rstrip('.').split(':')
            ret_value = int(z[0])*60 + int(z[1])
        return ret_value

    def compute_delta(lat, lon, dist, direction):
        R = 6371
        t = (math.tan(dist/R/2))**2
        c = 1
        if direction == 'lon':
            lat_rad = lat*math.pi/180
            c = (math.cos(lat_rad))**2
        d_rad = 2*math.asin(math.sqrt(t/(1+t)/c))
        return d_rad*180/math.pi

    def compute_distance(a_lat, a_lon, b_lat, b_lon):
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
        return self.pc

    def get_pc_as_str(self):
        return self.pc.to_string()


class PostcodeVisualiser():
    # TODO
    pass


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
        self.find_postcodes_button['command'] = self.fp_main
        self.find_postcodes_button.grid(row=6, column=3, padx=10)

        self.save_label = tk.Label(self, text='Save dataframe as ')
        self.save_label.grid(row=5, column=0, sticky=tk.E)
        self.save_entry = tk.Entry(self, width=8)
        self.save_entry.grid(row=5, column=1, columnspan=2, sticky=tk.W)

        self.visualisation_label = tk.Label(self, text='Draw map')
        self.visualisation_label.grid(row=6, column=0, sticky=tk.E)
        self.visualisation_CB = tk.Checkbutton(self)
        self.visualisation_CB.grid(row=6, column=1, sticky=tk.W)

        self.output_ST = tkst.ScrolledText(self, width=48)
        self.output_ST.grid(row=7, column=0, rowspan=4, columnspan=4)

    def fp_main(self):
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
        pcf = PostcodeFinder(input_dict)
        pcf.main()
        output_fname = self.save_entry.get().strip()
        if output_fname:
            pc_file = open(output_fname, 'wb')
            pickle.dump(pcf.get_pc_as_df(), pc_file)
            pc_file.close()
            print('Saved dataframe as "' + output_fname + '"')
        self.output_ST.insert(1.0, pcf.get_pc_as_str())
        # TODO : if statement for visualisation

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


pc_raw = pd.read_csv('postcode-outcodes.csv',
                     index_col='postcode', header=0).drop(columns=['id'])
pc_set = set(pc_raw.index)  # set of valid UK postcodes
root = tk.Tk()
root.title('Postcode Finder by PP')
app = Application(master=root)
app.mainloop()
