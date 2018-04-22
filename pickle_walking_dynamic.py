import pickle
import csv
from common_walking import STOP_LOCATIONS_CSV

def parse_csv():
    f = open(STOP_LOCATIONS_CSV)
    stop_csv = csv.reader(f)
    first = True
    stop_dict = {}
    stops = []
    for stop in stop_csv:
        if first:
            first = False ##skip the first row
            continue
        coord_str = (stop[3] + ',' + stop[4]).replace(" ", "")
        stop_name = stop[0]
        stop_dict[coord_str] = stop_name
        stops.append(coord_str)
    f.close()
    return (stops, stop_dict)

stops, stop_dict = parse_csv()
f = open("walking_dynamic.pickle",'wb')
pickle.dump((stops,stop_dict), f)
f.close()

