#!/usr/bin/env python3
import collections, operator
class IteratorPeeker:
    '''
    This class stores the next value from an iterator. You can call peek() to
    peek at this value as many times as you want. When you want the next value
    to be available, just call next().
    '''
    def __init__(self, iterator):
        self._stop_iteration = False
        self._iterator = iterator
        self._next = None
        self.next()
    def next(self):
        try:
            self._next = next(self._iterator)
        except StopIteration:
            self._stop_iteration = True
    def peek(self):
        if self._stop_iteration:
            raise StopIteration
        return self._next
def merge_selection(iterators, key=lambda x: x):
    '''
    This function yields values from the given iterators from smallest to
    largest. If two values are equal, the one from the iterator that is first
    in the arguments is yielded. This is consistent with built-in stability-
    preserving functions in Python.
    
    This function assumes that the iterators produce values from smallest to
    largest and that all the values from all the iterators can be compared
    with each other using the < operator.
    
    If the key argument is specified, then key(x) < key(y) will be used instead
    of x < y when determining the smallest value.
    '''
    # Create an IteratorPeeker for every iterator.
    # collections.deque is implemented in Python as a doubly-linked list.
    peekers = collections.deque(
        IteratorPeeker(iterator) for iterator in iterators
    )
    while peekers:
        # Peek the next values from the iterators.
        smallest_value = None
        peeker_smallest_value = None
        for peeker_index, peeker in enumerate(peekers):
            try:
                value = peeker.peek()
            except StopIteration:
                # This iterator has been fully consumed. Delete it.
                del peekers[peeker_index]
                # Go around! Now that the deque has mutated, it is a
                # RuntimeError to continue this iteration.
                smallest_value = None
                break
            if smallest_value is None or key(value) < key(smallest_value):
                smallest_value = value
                peeker_smallest_value = peeker
        # Find the smallest value.
        if smallest_value is not None:
            yield smallest_value
            peeker_smallest_value.next()
def departure_list(agencies, from_node, datetime_depart, max_count=None):
    '''
    Combines Directions that depart from from_node after datetime_depart from
    multiple agencies and yields them in order from earliest to latest.
    
    Arguments:
        agencies:
            an iterable of subclasses of agency_common.Agency
        from_node:
            a string that is either:
                a) the name of a bus stop, or
                b) whatever the user entered as the origin.
    '''
    for edge in merge_selection(
        (agency.get_pickup(from_node, datetime_depart) for agency in agencies),
        operator.attrgetter("datetime_depart")
    ):
        if max_count is not None:
            max_count -= 1
            if max_count < 0:
                return
        yield edge
