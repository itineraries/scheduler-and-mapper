#!/usr/bin/env python3
import attr, collections, datetime
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
    def get_columns_indices(self, from_node, to_node):
        '''
        Yields pairs of indices. In each pair, the first index corresponds to a
        value in self.header_row that is equal to from_node. In each pair, the
        second index corresponds to a value in self.header_row that is equal to
        to_node. In each pair, the first index is less than the second index.
        '''
        # There is no guarantee that all values in the header row are unique.
        # Also, there is no guarantee that from_node and to_node are different.
        # We assume that vehicles travel to the stops in the order in which
        # they are stored in the schedule from left to right; to_node must be
        # to the right of the from_node. Build lists of indices of from_node
        # and to_node in the header row.
        from_node_indices = []
        to_node_indices = collections.deque()
        for i, v in enumerate(self.header_row):
            if v == from_node:
                from_node_indices.append(i)
            # Because there is no guarantee that from_node and to_node are
            # different, we don't use elif here.
            if v == to_node:
                to_node_indices.append(i)
        # Find all pairs of a from_node index and a to_node index where the
        # former index is less than the latter. We can take advantage of the
        # fact that the two lists are sorted.
        for from_node_index in from_node_indices:
            # Pop off any values that are less than from_node_index.
            while to_node_indices and from_node_index >= to_node_indices[0]:
                to_node_indices.popleft()
            # Pair from_node_index with each of the remaining values.
            for to_node_index in to_node_indices:
                yield from_node_index, to_node_index
    def get_column_indices(self, from_node):
        '''
        Yields the indices that correspond to values in self.header_row that
        are equal to from_node.
        '''
        for i, v in enumerate(self.header_row):
            if v == from_node:
                yield i
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
