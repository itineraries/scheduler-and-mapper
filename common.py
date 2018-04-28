#!/usr/bin/env python3
import attr, base64, datetime, os.path, struct
from agency_common import Agency

def file_in_this_dir(name):
    return os.path.join(os.path.dirname(__file__), name)

NODE_LIST_TXT = file_in_this_dir("Node List.txt")
STOP_LOCATIONS_CSV = file_in_this_dir("Stop Locations.csv")

@attr.s
class Point:
    lat = attr.ib(converter=float)
    lng = attr.ib(converter=float)
    def __str__(self):
        return "{},{}".format(self.lat, self.lng)
@attr.s
class LineSegment:
    point_A = attr.ib(validator=attr.validators.instance_of(Point))
    point_B = attr.ib(validator=attr.validators.instance_of(Point))
    FilenameFriendlyStructFormat = "hffff"
    def to_filename_friendly(self, lowercase=True, precision=-1):
        '''
        Returns a case-insensitive string that represents this LineSegment.
        If precision is not negative, then the coordinates will be rounded to
        that many decimal places. The precision must be representable as a C
        short.
        '''
        s = base64.b32encode(
            struct.pack(
                self.FilenameFriendlyStructFormat,
                precision,
                self.point_A.lat,
                self.point_A.lng,
                self.point_B.lat,
                self.point_B.lng
            ) if precision < 0 else struct.pack(
                self.FilenameFriendlyStructFormat,
                precision,
                round(self.point_A.lat, precision),
                round(self.point_A.lng, precision),
                round(self.point_B.lat, precision),
                round(self.point_B.lng, precision),
            )
        ).decode("ASCII").rstrip('=')
        if lowercase:
            return s.lower()
        return s
    @classmethod
    def from_filename_friendly(cls, filename):
        '''
        Returns a LineSegment from a string from to_filename_friendly().
        '''
        precision, from_lat, from_lng, to_lat, to_lng = struct.unpack(
            cls.FilenameFriendlyStructFormat,
            base64.b32decode(
                filename.upper() + "=" * (7 - (len(filename) - 1) % 8)
            )
        )
        if precision >= 0:
            from_lat = round(from_lat, precision)
            from_lng = round(from_lng, precision)
            to_lat = round(to_lat, precision)
            to_lng = round(to_lng, precision)
        return cls(Point(from_lat, from_lng), Point(to_lat, to_lng))
    def to_pair_of_str(self):
        return (
            "{},{}".format(self.point_A.lat, self.point_A.lng),
            "{},{}".format(self.point_B.lat, self.point_B.lng)
        )
@attr.s(frozen=True)
class NodeAndTime:
    node = attr.ib(converter=str)
    time = attr.ib(validator=attr.validators.instance_of(datetime.datetime))
@attr.s
class Weight:
    # The datetime when the user leaves a node
    datetime_depart = attr.ib(
        default=datetime.datetime.min,
        validator=attr.validators.optional(
            attr.validators.instance_of(datetime.datetime)
        )
    )
    # The datetime when the user arrives at another node
    datetime_arrive = attr.ib(
        default=datetime.datetime.max,
        validator=attr.validators.optional(
            attr.validators.instance_of(datetime.datetime)
        )
    )
    # A string of a human-readable instruction
    human_readable_instruction = attr.ib(
        default=None,
        converter=attr.converters.optional(str)
    )
    # A tuple of NodeAndTime objects that represent stops that the vehicle
    # makes before the user disembarks
    intermediate_nodes = attr.ib(default=(), converter=tuple)
@attr.s(frozen=True)
class WeightedEdge(Weight):
    '''
    This class represents one instruction to the user within an itinerary.
    '''
    TIME_STRING = "at %I:%M %p on %A."
    agency = attr.ib(
        default=None,
        validator=attr.validators.optional(
            lambda self, attribute, value: issubclass(value, Agency)
        )
    )
    from_node = attr.ib(
        default=None,
        converter=attr.converters.optional(str)
    )
    to_node = attr.ib(
        default=None,
        converter=attr.converters.optional(str)
    )
    def __str__(self):
        result = []
        if self.datetime_depart is not None:
            result.append("Depart from")
            result.append(self.from_node)
            result.append(self.datetime_depart.strftime(self.TIME_STRING))
        if self.human_readable_instruction is not None:
            result.append(self.human_readable_instruction)
        if self.datetime_arrive is not None:
            result.append("Arrive at")
            result.append(self.to_node)
            result.append(self.datetime_arrive.strftime(self.TIME_STRING))
        return " ".join(result)
