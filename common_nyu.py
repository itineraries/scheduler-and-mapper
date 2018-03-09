#!/usr/bin/env python3
import attr, datetime
from common import file_in_this_dir
NYU_PICKLE = file_in_this_dir("NYU.pickle")
DAYS_OF_WEEK = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
)

@attr.s
class NYUSchedule:
    route = attr.ib(validator=attr.validators.instance_of(str))
    header_row = attr.ib(validator=attr.validators.instance_of(list))
    other_rows = attr.ib(validator=attr.validators.instance_of(list))
    header_row_reverse = attr.ib(
        attr.validators.optional(
            attr.validators.instance_of(dict)
        )
    )
@attr.s
class NYUTime:
    def __str__(self):
        options = ["DO"] # drop-off is always available
        if self.pickup:
            options.append("PU")
        if self.soft:
            options.append("Soft")
        return str(self.time) + \
            (" (" + ", ".join(options) + ")" if options else "")
    def __bool__(self):
        return bool(self.time)
    # Instead of representing the time as a time object, the time should be
    # represented as the amount of time since midnight. This allows schedules
    # to wrap to the next day.
    time = attr.ib(validator=attr.validators.instance_of(datetime.timedelta))
    # If True, then the user can board the vehicle at this time.
    pickup = attr.ib(validator=attr.validators.instance_of(bool))
    # If True, a rider must signal the driver to stop here.
    soft = attr.ib(validator=attr.validators.instance_of(bool), default=False)
