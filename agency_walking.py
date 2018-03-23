#!/usr/bin/env python3
import datetime, pickle
from agency_common import Agency
from common_walking import WALKING_TIMES_PICKLE

ONE_MINUTE = datetime.timedelta(minutes=1)

with open(WALKING_TIMES_PICKLE, "rb") as f:
    WALKING_TIMES = pickle.load(f)

class AgencyWalking(Agency):
    max_seconds = (
        datetime.datetime.max - datetime.datetime.min
    ).total_seconds()
    @classmethod
    def add_arguments(cls, arg_parser_add_argument):
        arg_parser_add_argument(
            "--walking-max",
            type=float,
            default=cls.max_seconds / 60.0,
            help="in minutes, the longest you are willing to walk at a time"
        )
    @classmethod
    def handle_parsed_arguments(cls, args_parsed):
        max_seconds = args_parsed.walking_max * 60.0 # convert from minutes
        if max_seconds <= cls.max_seconds:
            cls.max_seconds = max_seconds
        else:
            print("Warning: --walking-max was changed to", cls.max_seconds)
    @classmethod
    def get_edge(
        cls,
        from_node,
        to_node,
        datetime_depart=datetime.datetime.min,
        datetime_arrive=datetime.datetime.max,
        consecutive_agency=None
    ):
        # Do not allow consecutive walking instructions.
        if consecutive_agency != cls:
            try:
                seconds, directions_file = WALKING_TIMES[(from_node, to_node)]
            except KeyError:
                # Walking directions are not available between these two nodes
                # in this direction. Yield nothing.
                pass
            else:
                # Walking directions don't change based on the time.
                # Yield trips one minute apart.
                if seconds < cls.max_seconds:
                    travel_duration = datetime.timedelta(seconds=seconds)
                    if datetime_depart == datetime.datetime.min and \
                        datetime_arrive != datetime.datetime.max:
                        # Yield the latest trip and then go back in time.
                        if datetime_arrive > datetime.datetime.min + \
                            travel_duration:
                            datetime_depart = datetime_arrive - travel_duration
                            while True:
                                yield cls.UnweightedEdge(
                                    datetime_depart,
                                    datetime_arrive,
                                    human_readable_instruction="Walk."
                                )
                                if datetime_depart - datetime.datetime.min <= \
                                    ONE_MINUTE:
                                    break
                                datetime_depart -= ONE_MINUTE
                                datetime_arrive -= ONE_MINUTE
                    else:
                        # Yield the earliest trip and then go forward in time.
                        stop = datetime_arrive
                        if datetime_depart < \
                            datetime.datetime.max - travel_duration and \
                            datetime_arrive > \
                            datetime.datetime.min + travel_duration:
                            datetime_arrive = datetime_depart + travel_duration
                            while True:
                                yield cls.UnweightedEdge(
                                    datetime_depart,
                                    datetime_arrive,
                                    human_readable_instruction="Walk."
                                )
                                if datetime.datetime.max - datetime_arrive <= \
                                    ONE_MINUTE:
                                    break
                                datetime_depart += ONE_MINUTE
                                datetime_arrive += ONE_MINUTE
