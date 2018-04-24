#!/usr/bin/env python3
import csv
from common import Point, STOP_LOCATIONS_CSV
'''
Reads the CSV file written by match_stops_locations creates the following
properties:
    name_to_point:
        A dictionary where the keys are the stop names and the values are
        Point objects that represent the locations of the stops
    geo_str_to_name:
        A dictionary where the keys are string representations of Point
        objects and the values are the stop names
'''
name_to_point = {}
geo_str_to_name = {}
with open(STOP_LOCATIONS_CSV, "r", newline="", encoding="UTF-8") as f:
    for row in csv.DictReader(f):
        p = Point(lat=row["Latitude"], lng=row["Longitude"])
        name_to_point[row["From PDFs"]] = p
        geo_str_to_name[str(p)] = row["From PDFs"]
