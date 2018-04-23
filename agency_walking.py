#!/usr/bin/env python3
import datetime
from agency_common import Agency

_added_arguments = False
_handled_arguments = False

class AgencyWalking(Agency):
    '''
    The purpose of this class is to add the --walking-max argument to the
    command line. Agencies whose edges involve walking should subclass this
    class and check the max_seconds property; the user should not be suggested
    to walk more that this number of seconds at a time.
    
    Agencies whose edges involve walking should also make sure that the
    consecutive_agency parameter to get_edge is not a subclass of this one.
    This will prevent consecutive walking directions in the itinerary.
    
    This class does not implement get_edge, so it cannot yield edges. However,
    subclasses of this class may implement get_edge.
    '''
    max_seconds = (
        datetime.datetime.max - datetime.datetime.min
    ).total_seconds()
    @classmethod
    def add_arguments(cls, arg_parser_add_argument):
        if not _added_arguments:
            arg_parser_add_argument(
                "--walking-max",
                type=float,
                default=cls.max_seconds / 60.0,
                metavar="minutes",
                help=
                    "the longest period of time that you are willing to walk "
                    "at a time without using some other form of transportation"
            )
            _added_arguments = True
    @classmethod
    def handle_parsed_arguments(cls, args_parsed):
        if not _handled_arguments:
            max_seconds = args_parsed.walking_max * 60.0
            if max_seconds <= cls.max_seconds:
                cls.max_seconds = max_seconds
            else:
                print("Warning: --walking-max was changed to", cls.max_seconds)
            _handled_arguments = True
