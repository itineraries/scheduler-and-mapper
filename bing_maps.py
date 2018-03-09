#!/usr/bin/env python3
import json, keyring, urllib.parse, urllib.request
from datetime import datetime, time
_apikey = keyring.get_password("bing_maps", "default")
TIME_TYPE_ARRIVE = 0
TIME_TYPE_DEPART = 1
TIME_TYPE_LAST_AVAIL = 2
_time_type_map = {
    TIME_TYPE_ARRIVE: "Arrival",
    TIME_TYPE_DEPART: "Departure",
    TIME_TYPE_LAST_AVAIL: "LastAvailable"
}
TRAVEL_MODE_WALKING = 0
TRAVEL_MODE_TRANSIT = 1
TRAVEL_MODE_DRIVING = 2
_travel_mode_map = {
    TRAVEL_MODE_WALKING: "Walking",
    TRAVEL_MODE_TRANSIT: "Transit",
    TRAVEL_MODE_DRIVING: "Driving"
}
def get_route(
    waypoints, time_type=TIME_TYPE_ARRIVE, dt=datetime.now(),
    travel_mode=TRAVEL_MODE_TRANSIT, metric_system=True, decode_json=True
):
    '''
    Uses the Bing Maps API to get directions. See
    https://msdn.microsoft.com/en-us/library/ff701717.aspx for API information.
    If the request fails, urllib.error.URLError may be raised.
    
    Arguments:
        waypoints:
            A list of places that the route will pass through
        time_type:
            Whether dt should indicate the arrival time or the departure time
        dt:
            A datetime
        travel_mode:
            Walking, transit, or driving
        metric_system:
            Use kilometers if True, miles if False
        decode_json:
            If True, the data from the API will be parsed as JSON before being
            returned. If False, the data will be returned as bytes.
    '''
    assert isinstance(dt, datetime)
    assert time_type in _time_type_map, "Invalid time type"
    assert travel_mode in _travel_mode_map, "Invalid travel mode"
    # Add waypoints to URL parameters.
    parameters = {
        "waypoint.{:d}".format(n): v
        for n, v
        in enumerate(waypoints, start=1)
    }
    # Add other parameters to URL.
    parameters.update({
        'dateTime': dt.strftime("%Y-%m-%d %I:%M %p"),
        'timeType': _time_type_map[time_type],
        'distanceUnit': "km" if metric_system else "mi",
        'key': _apikey
    })
    url = "https://dev.virtualearth.net/REST/v1/Routes/" + \
        _travel_mode_map[travel_mode] + "?" + urllib.parse.urlencode(parameters)
    # Send request.
    r = urllib.request.urlopen(url)
    try:
        if decode_json:
            return json.loads(r.read().decode("UTF-8"))
        return r.read()
    finally:
        r.close()
