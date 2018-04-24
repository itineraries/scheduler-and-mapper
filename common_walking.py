#!/usr/bin/env python3
import attr, base64, struct

@attr.s
class Point:
    lat = attr.ib(converter=float)
    lng = attr.ib(converter=float)
@attr.s
class Edge:
    from_node = attr.ib(validator=attr.validators.instance_of(Point))
    to_node = attr.ib(validator=attr.validators.instance_of(Point))
    FilenameFriendlyStructFormat = "hffff"
    def to_filename_friendly(self, lowercase=True, precision=-1):
        '''
        Returns a case-insensitive string that represents this Edge.
        If precision is not negative, then the coordinates will be
        rounded to that many decimal places. The precision must be
        representable as a C short.
        '''
        s = base64.b32encode(
            struct.pack(
                self.FilenameFriendlyStructFormat,
                precision,
                self.from_node.lat,
                self.from_node.lng,
                self.to_node.lat,
                self.to_node.lng
            ) if precision < 0 else struct.pack(
                self.FilenameFriendlyStructFormat,
                precision,
                round(self.from_node.lat, precision),
                round(self.from_node.lng, precision),
                round(self.to_node.lat, precision),
                round(self.to_node.lng, precision),
            )
        ).decode("ASCII").rstrip('=')
        if lowercase:
            return s.lower()
        return s
    @classmethod
    def from_filename_friendly(cls, filename):
        '''
        Returns an Edge from a string from to_filename_friendly().
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
            "{},{}".format(self.from_node.lat, self.from_node.lng),
            "{},{}".format(self.to_node.lat, self.to_node.lng)
        )
