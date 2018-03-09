#!/usr/bin/env python3
import attr
from common import file_in_this_dir
STOP_LOCATIONS_CSV = file_in_this_dir("Stop Locations.csv")

@attr.s
class Point:
    lat = attr.ib(converter=float)
    lng = attr.ib(converter=float)
