#!/usr/bin/env python3
import argparse, datetime, dateutil.parser, os, pickle, warnings
from shortestpathfinder import ShortestPathFinder
from common import NODE_LIST_TXT
from agency_common import Agency
from agency_nyu import AgencyNYU
from agency_walking_static import AgencyWalkingStatic

def parse_args(agencies=()):
    arg_parser = argparse.ArgumentParser(
        description=
            "Given an origin, a destination, an arrival or departure time, "
            "and optional restrictions (see below), returns directions on how "
            "to get from the origin to the destination by walking and/or by "
            "taking the NYU buses."
    )
    # Add arguments for this script.
    arg_parser.add_argument(
        "origin",
        help="the place that you are coming from"
    )
    arg_parser.add_argument(
        "destination",
        help="the place that you want to go to"
    )
    arg_parser.add_argument(
        "datetime",
        help=
            "if --depart is set, the earliest time that you can depart from "
            "the origin; "
            "if --depart is not set, the latest time that you can arrive at "
            "the destination"
    )
    arg_parser.add_argument(
        "-d",
        "--depart",
        action="store_true",
        help="modifies the behavior of datetime (see above)"
    )
    # Allow agencies to add their own arguments.
    for agency in agencies:
        agency.add_arguments(arg_parser.add_argument)
    # Parse the arguments.
    args_parsed = arg_parser.parse_args()
    args_parsed.origin = args_parsed.origin.strip()
    args_parsed.destination = args_parsed.destination.strip()
    # Convert the datetime argument to a datetime.
    if args_parsed.datetime.lower() == "now":
        args_parsed.datetime = datetime.datetime.now()
    else:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                args_parsed.datetime = \
                    dateutil.parser.parse(args_parsed.datetime)
            if args_parsed.datetime.tzinfo is not None:
                raise dateutil.parser._parser.UnknownTimezoneWarning
        except ValueError:
            arg_parser.error(
                "invalid datetime value: " + repr(args_parsed.datetime)
            )
        except dateutil.parser._parser.UnknownTimezoneWarning:
            # Time zones are not currently supported by this software.
            arg_parser.error("time zones are not supported")
    # Pass the parsed arguments to the agencies.
    for agency in agencies:
        agency.handle_parsed_arguments(args_parsed)
    # Return the parsed arguments.
    return args_parsed
def main():
    with open(NODE_LIST_TXT, "r", encoding="UTF-8") as f:
        nodes = [line.strip() for line in f]
    agencies = (
        AgencyNYU,
        AgencyWalkingStatic,
    )
    assert all(issubclass(a, Agency) or isinstance(a, Agency) for a in agencies)
    args_parsed = parse_args(agencies)
    if False:
        pass
    else:
        if args_parsed.origin != args_parsed.destination:
            pathfinder = ShortestPathFinder(nodes, agencies)
            trip = pathfinder.find_trip(
                args_parsed.origin,
                args_parsed.destination,
                args_parsed.datetime,
                args_parsed.depart
            )
            if trip:
                print("Itinerary:")
                for direction in trip:
                    print(" -", direction)
                print(
                    "Total time:",
                    trip[-1].datetime_arrive - trip[0].datetime_arrive
                    if args_parsed.depart else
                    trip[-1].datetime_depart - trip[0].datetime_depart
                )
            else:
                print(pathfinder.error)
        else:
            print("The origin and the destination are the same. That was easy.")

if __name__ == "__main__":
    main()
