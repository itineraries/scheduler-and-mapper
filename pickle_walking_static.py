#!/usr/bin/env python3
'''
Use this script to prepare the pickle that agency_walking_static needs.

Before running this script, make sure that all stops are in the node list
and run match_stops_locations.
'''
import errno, itertools, json, os, pickle, sys
from common import file_in_this_dir, LineSegment
from common_walking_static import WALKING_TIMES_PICKLE
import bing_maps, stops
WALKING_DIRECTORY = file_in_this_dir("Walking")

def walking_directions_filename(line):
    # Round to the nearest 0.00001, which is a
    # little more than a meter at the equator.
    return os.path.join(
        WALKING_DIRECTORY,
        "Walking_Directions_" + line.to_filename_friendly(
            precision=5
        ) + ".json"
    )
def all_lines():
    '''
    Takes stops.name_to_point and yields a (name, name, LineSegment, filename)
    tuple from every location to every other location. The filename refers to
    the name of the file in which the API response should be cached.
    '''
    for (from_name, from_node), (to_name, to_node) in itertools.permutations(
        stops.name_to_point.items(),
        2
    ):
        line = LineSegment(from_node, to_node)
        filename = walking_directions_filename(line)
        yield from_name, to_name, line, filename
def main():
    # Create WALKING_DIRECTORY if it does not exist.
    try:
        os.makedirs(WALKING_DIRECTORY)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    # Figure out which walking directions are missing.
    walking_times = {}
    try:
        for from_name, to_name, line, filename in all_lines():
            # Get walking directions.
            try:
                # If the walking directions are cached, read them from cache.
                with open(filename, "rb") as f:
                    d = f.read()
            except FileNotFoundError:
                # The walking directions were not cached. Get them from Bing.
                d = bing_maps.get_route(
                    line.to_pair_of_str(),
                    travel_mode=bing_maps.TRAVEL_MODE_WALKING,
                    decode_json=False
                )
                # Save the whole response to a file.
                with open(filename, "wb") as f:
                    f.write(d)
                print("Queried Bing for walking directions", end="")
            else:
                print("Using cached directions", end="")
            print(
                " from ", repr(from_name),
                " to ", repr(to_name),
                " (cache file: ", filename, ")",
                sep=""
            )
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
