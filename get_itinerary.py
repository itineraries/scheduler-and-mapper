#!/usr/bin/env python3
import argparse, datetime, dateutil.parser, warnings
import agency_common, agency_nyu, agency_walking_static, \
    agency_walking_dynamic, departure_lister, itinerary_finder
TIME_FORMAT = "%I:%M %p on %A"

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
        help="the place that you want to go to",
        nargs="?",
        default=""
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
    arg_parser.add_argument(
        "-l",
        "--list-departures",
        type=int,
        nargs="?",
        const=2,
        default=0,
        metavar="N",
        help=
            "(implies --depart) if set, instead of directions to the "
            "destination, the next N departures from the origin after "
            "datetime are returned"
    )
    arg_parser.add_argument(
        "-n",
        "--number-of-itineraries",
        type=int,
        default=0,
        metavar="N",
        help=
            "causes N different itineraries to be printed instead of just the "
            "one that is the most optimal"
    )
    # Allow agencies to add their own arguments.
    for agency in agencies:
        agency.add_arguments(arg_parser.add_argument)
    # Parse the arguments.
    args_parsed = arg_parser.parse_args()
    args_parsed.origin = args_parsed.origin.strip()
    args_parsed.destination = args_parsed.destination.strip()
    # Check that the destination or --list-departures was specified and that
    # only one, not both, was specified.
    if args_parsed.destination and args_parsed.list_departures:
        arg_parser.error(
            "the destination and --list-departures are mutually exclusive"
        )
    elif not args_parsed.destination and not args_parsed.list_departures:
        arg_parser.error(
            "either the destination or --list-departures is required"
        )
    # Check that --list-departures and --number-of-itineraries are not both
    # set.
    if args_parsed.list_departures and args_parsed.number_of_itineraries:
        arg_parser.error(
            "--list-departures cannot be used with --number-of-itineraries"
        )
    # Check that --number-of-itineraries is at least 1 or that it is 0.
    if args_parsed.number_of_itineraries < 0:
        arg_parser.error("--number-of-itineraries must be 1 or more")
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
        agency.handle_parsed_arguments(args_parsed, arg_parser.error)
    # Return the parsed arguments.
    return args_parsed
def print_weighted_edge(edge, bullet):
    margin = " " * len(bullet)
    print(bullet, edge.get_human_readable_instruction())
    print(
        margin,
        "- {}: Depart from {}.".format(
            edge.datetime_depart.strftime(TIME_FORMAT),
            edge.from_node
        )
    )
    if edge.intermediate_nodes:
        print(margin, "- Intermediate stops:")
        for j, node_and_time in enumerate(edge.intermediate_nodes, start=1):
            print(
                margin,
                "  {:>3}. {}: {}".format(
                    j,
                    node_and_time.time.strftime(TIME_FORMAT),
                    node_and_time.node
                )
            )
    print(
        margin,
        "- {}: Arrive at {}.".format(
            edge.datetime_arrive.strftime(TIME_FORMAT),
            edge.to_node
        )
    )
def main():
    agencies = (
        agency_nyu.AgencyNYU,
        agency_walking_static.AgencyWalkingStatic,
        agency_walking_dynamic.AgencyWalkingDynamic,
    )
    agencies_to_vary = (
        agency_nyu.AgencyNYU,
    )
    assert all(issubclass(a, agency_common.Agency) for a in agencies)
    args_parsed = parse_args(agencies)
    if args_parsed.list_departures:
        # The user asked for a list of departures from the origin.
        print("Departures:")
        for direction in departure_lister.departure_list(
            agencies,
            args_parsed.origin,
            args_parsed.datetime,
            args_parsed.list_departures
        ):
            print_weighted_edge(direction, " -")
    elif args_parsed.origin != args_parsed.destination:
        # The user specified a destination.
        if args_parsed.number_of_itineraries:
            # The user wants multiple itineraries.
            print("Itineraries:")
            for i, itinerary in enumerate(
                itinerary_finder.find_itineraries(
                    agencies_to_vary,
                    agencies,
                    args_parsed.origin,
                    args_parsed.destination,
                    args_parsed.datetime,
                    args_parsed.depart,
                    max_count=args_parsed.number_of_itineraries
                ),
                start=1
            ):
                print(" - Itinerary #{}:".format(i))
                for i, direction in enumerate(itinerary, start=1):
                    print_weighted_edge(direction, "   {:>3}.".format(i))
                print(
                    "   Total time:",
                    itinerary[-1].datetime_arrive - 
                    itinerary[0].datetime_depart
                )
        else:
            # The user only wants one itinerary.
            try:
                itinerary = itinerary_finder.find_itinerary(
                    agencies,
                    args_parsed.origin,
                    args_parsed.destination,
                    args_parsed.datetime,
                    args_parsed.depart
                )
            except itinerary_finder.ItineraryNotPossible:
                print(
                    "This itinerary is not possible either because there is "
                    "no continuous path from the origin to the destination or "
                    "because no agency recognized the origin or destination."
                )
            else:
                print("Itinerary:")
                for i, direction in enumerate(itinerary, start=1):
                    print_weighted_edge(direction, "{:>3}.".format(i))
                print(
                    "Total time:",
                    itinerary[-1].datetime_arrive - 
                    itinerary[0].datetime_depart
                )
    else:
        print("The origin and the destination are the same.")

if __name__ == "__main__":
    main()
