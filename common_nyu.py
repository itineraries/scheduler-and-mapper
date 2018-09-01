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

def _deques_increasing_first(list_of_deques, greater_than=None):
    '''
    Yields tuples. In each tuple, a) each item is a value from a deque and
    b) each item is greater than the previous. The first item is greater than
    greater_than. This generator yields all combinations that satisfy these
    conditions. It is assumed that the deques are sorted in ascending order.
    '''
    if list_of_deques:
        # Get the first deque in the list of deques.
        q = list_of_deques[0]
        # Get the first value in the deque that is greater than greater_than.
        # Discard all values before it.
        if greater_than is not None:
            try:
                while q[0] <= greater_than:
                    q.popleft()
            except IndexError:
                # This deque is empty. The generator must terminate.
                return
        # At this point, the first value in the deque is greater than
        # greater_than.
        for value in q:
            # Construct the tuple, starting with the value from the deque.
            head = (value,)
            # If there are more deques, values from them will form the rest of
            # the tuple. Otherwise, just yield the head with no tail.
            if len(list_of_deques) > 1:
                # Recursively call this generator on the rest of the deques.
                for tail in _deques_increasing_first(
                    list_of_deques[1:],
                    value
                ):
                    yield head + tail
            else:
                yield head

@attr.s
class NYUSchedule:
    route = attr.ib(validator=attr.validators.instance_of(str))
    header_row = attr.ib(validator=attr.validators.instance_of(list))
    other_rows = attr.ib(validator=attr.validators.instance_of(list))
    days_of_week = attr.ib()
    def get_columns_indices(self, *nodes):
        '''
        Yields tuples of indices. In each tuple, the nth item is an index of
        self.header_row where the value equals the nth argument (not counting
        self). In each tuple, every item is greater than the last.
        '''
        # There is no guarantee that all values in the header row are unique.
        # Also, there is no guarantee that the requested nodes are different.
        # We assume that vehicles travel to the stops in the order in which
        # they are stored in the schedule from left to right; each node must be
        # to the right of the last.
        nodes_occurrences = [collections.deque() for _ in nodes]
        for index, header in enumerate(self.header_row):
            for occurrences, node in zip(nodes_occurrences, nodes):
                if header == node:
                    occurrences.append(index)
        # Find combinations of indices. Each combination contains one index of
        # an occurrence of each requested node. We can take advantage of the
        # fact that the lists of indices of occurrences are sorted.
        return _deques_increasing_first(nodes_occurrences)
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
