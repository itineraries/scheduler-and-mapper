#!/usr/bin/env python3
'''
Use this script to prepare the pickle that agency_walking needs.

Before running this script, make sure that all stops are in the node list
and run match_stops_locations.
'''
import csv, errno, itertools, json, os, pickle, sys
from common import file_in_this_dir
from common_walking import WALKING_TIMES_PICKLE, STOP_LOCATIONS_CSV, Point, \
    Edge
import bing_maps
WALKING_DIRECTORY = file_in_this_dir("Walking")

def walking_directions_filename(edge):
    # Round to the nearest 0.00001, which is a
    # little more than a meter at the equator.
    return os.path.join(
        WALKING_DIRECTORY,
        "Walking_Directions_" + edge.to_filename_friendly(
            precision=5
        ) + ".json"
    )
def read_stop_locations(filename):
    '''
    Reads the CSV file written by match_stops_locations
    and returns a dictionary from each stop name to its
    location, represented by a Point.
    '''
    with open(filename, "r", newline="") as f:
        return {
            row["From PDFs"]: Point(
                lat=row["Latitude"],
                lng=row["Longitude"]
            )
            for row
            in csv.DictReader(f)
        }
def all_edges(stop_locations_dict):
    '''
    Takes a dictionary from read_stop_locations and
    yields a (name, name, Edge) tuple from every
    location to every other location.
    '''
    for (from_name, from_node), (to_name, to_node) in itertools.permutations(
        stop_locations_dict.items(),
        2
    ):
        yield from_name, to_name, Edge(from_node, to_node)
def edges_without_directions(edges_iterable):
    '''
    Takes the generator from all_edges, and only
    returns the ones that are not cached.
    '''
    for from_name, to_name, edge in edges_iterable:
        filename = walking_directions_filename(edge)
        if not os.path.exists(filename):
            yield from_name, to_name, edge, filename
def main():
    # Create WALKING_DIRECTORY if it does not exist.
    try:
        os.makedirs(WALKING_DIRECTORY)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    # Add to the existing pickle if it exists.
    try:
        with open(WALKING_TIMES_PICKLE, "rb") as f:
            walking_times = pickle.load(f)
    except FileNotFoundError:
        walking_times = {}
    # Figure out which walking directions are missing.
    try:
        for from_name, to_name, edge, filename in edges_without_directions(
            all_edges(read_stop_locations(STOP_LOCATIONS_CSV))
        ):
            print("From", repr(from_name), "to", repr(to_name), "in", filename)
            # Query Bing for walking directions.
            d = bing_maps.get_route(
                edge.to_pair_of_str(),
                travel_mode=bing_maps.TRAVEL_MODE_WALKING,
                decode_json=False
            )
            # Save the whole response to a file.
            with open(filename, "wb") as f:
                f.write(d)
            # Extract the travel time.
            seconds = json.loads(
                d.decode("UTF-8")
            )["resourceSets"][0]["resources"][0]["travelDuration"]
            # Save a reference to this response in the dictionary.
            walking_times[(from_name, to_name)] = (seconds, filename)
    finally:
        print("Saving pickle...")
        with open(WALKING_TIMES_PICKLE, "wb") as f:
            pickle.dump(walking_times, f)
    print("Done.")

if __name__ == "__main__":
    main()
