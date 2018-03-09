#!/usr/bin/env python3
import argparse, datetime, dateutil.parser, os, pickle
from shortestpathfinder import ShortestPathFinder
from common import NODE_LIST_TXT
from agency_common import Agency
from agency_walking import AgencyWalking
TIME_STRING = "%I:%M %p"

def parse_args(agencies=()):
    arg_parser = argparse.ArgumentParser(
        description="Finds a trip in a schedule"
    )
    # Add arguments for this script.
    arg_parser.add_argument("origin", help="the origin of the trip")
    arg_parser.add_argument("destination", help="the destination of the trip")
    arg_parser.add_argument(
        "datetime",
        help=
            "the date and time that the trip starts if --depart "
            "is set or ends if --depart is not set"
    )
    arg_parser.add_argument(
        "-d",
        "--depart",
        action="store_true",
        help="if present, the trip starts instead of ends at the specified time"
    )
    arg_parser.add_argument(
        "-s",
        "--schedule-directory",
        default=os.curdir,
        help=
            "the directory in which to look for schedule "
            "pickles from pickle_schedules.py"
    )
    # Allow agencies to add their own arguments.
    for agency in agencies:
        agency.add_arguments(arg_parser.add_argument)
    # Parse the arguments.
    args_parsed = arg_parser.parse_args()
    # Pass the parsed arguments to the agencies.
    for agency in agencies:
        agency.handle_parsed_arguments(args_parsed)
    # Return the parsed arguments.
    return args_parsed
def main():
    with open(NODE_LIST_TXT, "r") as f:
        nodes = [line.strip() for line in f]
    agencies = (
        AgencyWalking,
    )
    assert all(issubclass(a, Agency) or isinstance(a, Agency) for a in agencies)
    args_parsed = parse_args(agencies)
    # Convert the datetime argument to a datetime.
    try:
        if args_parsed.datetime.lower() == "now":
            args_parsed.datetime = datetime.datetime.now()
        else:
            args_parsed.datetime = dateutil.parser.parse(
                args_parsed.datetime,
                ignoretz=True
            )
    except ValueError:
        arg_parser.print_usage()
        print("{}: error: argument datetime: invalid datetime value: {}".format(
            __file__,
            repr(args_parsed.datetime))
        )
    else:
        args_parsed.origin = args_parsed.origin.strip()
        args_parsed.destination = args_parsed.destination.strip()
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
                for \
                    stop_depart, time_depart, instruction, \
                    stop_arrive, time_arrive\
                in trip:
                    print(end=" - ")
                    if time_depart is not None:
                        print(
                            "Depart from", stop_depart, "at",
                            time_depart.strftime(TIME_STRING),
                            end=". "
                        )
                    if instruction is not None:
                        print(instruction, end=" ")
                    if time_arrive is not None:
                        print(
                            "Arrive at", stop_arrive, "at",
                            time_arrive.strftime(TIME_STRING),
                            end="."
                        )
                    print()
                print(
                    "Total time:",
                    trip[-1][4] - trip[0][4]
                    if args_parsed.depart else
                    trip[-1][1] - trip[0][1]
                )
            else:
                print(pathfinder.error)
        else:
            print("The origin and the destination are the same. That was easy.")

if __name__ == "__main__":
    main()
