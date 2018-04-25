#!/usr/bin/env python3
import datetime
from agency_common import Agency

_added_arguments = False
_handled_arguments = False
_max_seconds_unlimited = (
    datetime.datetime.max - datetime.datetime.min
).total_seconds()
_max_seconds = _max_seconds_unlimited

def set_max_seconds(value):
    _max_seconds = value
def set_max_seconds_unlimited():
    _max_seconds = _max_seconds_unlimited

class MaxSecondsGet:
    def __get__(self, instance, owner):
        return _max_seconds
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
    max_seconds = MaxSecondsGet()
    @staticmethod
    def add_arguments(arg_parser_add_argument):
        global _added_arguments
        if not _added_arguments:
            arg_parser_add_argument(
                "--walking-max",
                type=float,
                default=_max_seconds_unlimited / 60.0,
                metavar="minutes",
                help=
                    "the longest period of time that you are willing to walk "
                    "at a time without using some other form of transportation"
            )
            _added_arguments = True
    @staticmethod
    def handle_parsed_arguments(args_parsed, arg_parser_error):
        global _handled_arguments, _max_seconds
        if not _handled_arguments:
            max_seconds = args_parsed.walking_max * 60.0
            if 0.0 <= max_seconds <= _max_seconds_unlimited:
                _max_seconds = max_seconds
            else:
                arg_parser_error(
                    "--walking-max must be between 0.0 and " +
                    str(_max_seconds_unlimited / 60.0)
                )
            _handled_arguments = True
