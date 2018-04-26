#!/usr/bin/env python3
import collections, datetime, heapq, itertools, pickle
from agency_common import Agency
from common import Weight, WeightedEdge
from common_nyu import NYU_PICKLE
JUST_BEFORE_MIDNIGHT = datetime.timedelta(microseconds=-1)
MIDNIGHT = datetime.time()
ONE_DAY = datetime.timedelta(days=1)

with open(NYU_PICKLE, "rb") as f:
    schedule_by_day = pickle.load(f)

def timedelta_after_midnight(dt):
    '''
    Separates a datetime.datetime object into a datetime.date object and a
    datetime.timedelta object that represents the amount of time after midnight
    on the same day.
    '''
    return (
        dt.date(),
        datetime.timedelta(
            seconds=dt.second,
            microseconds=dt.microsecond,
            minutes=dt.minute,
            hours=dt.hour
        )
    )
def first_greater_than(l, v, key=None, min_index=0, max_index=None):
    '''
    Returns the index of the first value in l that is greater than v. If the
    greatest value in l is not greater than v, then ValueError is raised.
    
    Arguments:
        l: a list
        v: a value
        key: if not None, v will be compared to key(l[i]) instead of l[i]
        min_index: only search starting at this index in l
        max_index: only search up to but not including this index in l
    '''
    if not l:
        raise ValueError("The list is empty.")
    if max_index is None:
        max_index = len(l)
    if key is None:
        key = lambda x: x
    # If the two indices are equal, there is nothing left to search.
    if min_index == max_index:
        if max_index < len(l):
            return max_index
        raise ValueError("The greatest value is " + str(l[-1]) + ".")
    # Here is the good old binary search.
    mid_index = (min_index + max_index) // 2
    if v < key(l[mid_index]):
        return first_greater_than(l, v, key, min_index, mid_index)
    return first_greater_than(l, v, key, mid_index + 1, max_index)

EdgeHeapQKey = collections.namedtuple("EdgeHeapQKey", ("key", "edge"))
class AgencyNYU(Agency):
    @classmethod
    def get_edge(
        cls,
        from_node,
        to_node,
        datetime_depart=datetime.datetime.min,
        datetime_arrive=datetime.datetime.max,
        consecutive_agency=None
    ):
        backwards = \
            datetime_depart == datetime.datetime.min and \
            datetime_arrive != datetime.datetime.max
        if backwards:
            date_arrive, timedelta_arrive = timedelta_after_midnight(
                datetime_arrive
            )
            first_arrival = datetime.datetime.max
        else:
            date_depart, timedelta_depart = timedelta_after_midnight(
                datetime_depart
            )
            # To account for schedules that run past midnight and from the
            # previous day, we start our search in the previous day but with
            # one day added to the timedelta.
            try:
                date_depart -= ONE_DAY
            except OverflowError:
                # The date should only overflow if datetime_depart was within
                # a day of the minimum. I cannot see why any user would want
                # to check schedules that far into the past, but I also cannot
                # see why I should not account for this. If we cannot roll the
                # date back by a day, just start searching normally.
                pass
            else:
                timedelta_depart += ONE_DAY
            last_departure = datetime.datetime.min
        # Use a priority queue as a buffer for edges. This allows us to
        # make sure that we have scanned all the schedules at least one day
        # ahead before we determine which is the soonest trip and yield it.
        edges_heap = []
        date_overflowed = False
        days_without_edges = 0
        # Yield edges until we hit the maximum date.
        while True:
            # If the departure times of the edges in the buffer do not span
            # at least a day, compute more edges. If no departures are seen
            # in seven days, just stop; there will not be any more because
            # the schedules repeat every week.
            if days_without_edges < 7 and (
                not edges_heap or
                (
                    edges_heap[0].edge.datetime_arrive - first_arrival
                    if backwards else
                    last_departure - edges_heap[0].edge.datetime_depart
                ) < ONE_DAY
            ) and not date_overflowed:
                days_without_edges += 1
                for schedule in schedule_by_day[
                    (date_arrive if backwards else date_depart).weekday()
                ]:
                    for from_node_index, to_node_index \
                        in schedule.get_columns_indices(from_node, to_node):
                        # Filter out the rows with None for either stop and
                        # rows where pickup is unavailable from from_node.
                        # Recall that from_node_index < to_node_index is
                        # guaranteed by schedule.get_columns_indices.
                        times = [
                            (row[from_node_index], row[to_node_index])
                            for row in schedule.other_rows
                            if to_node_index < len(row)
                            and row[from_node_index] is not None
                            and row[from_node_index].pickup
                            and row[to_node_index] is not None
                        ]
                        try:
                            if backwards:
                                # Find the first row in the schedule where the
                                # arrival time is greater than
                                # timedelta_arrive. We only want to look at the
                                # rows in the schedule above this row. The row
                                # before this one is the last row where the
                                # arrival time is less than timedelta_arrive.
                                ending_index = first_greater_than(
                                    times,
                                    timedelta_arrive,
                                    lambda x: x[1].time
                                )
                            else:
                                # Find the first row in the schedule where the
                                # departure time is greater than
                                # timedelta_depart. We only want to look at
                                # this row and the rows in the schedule that
                                # are below this row.
                                starting_index = first_greater_than(
                                    times,
                                    timedelta_depart,
                                    lambda x: x[0].time
                                )
                        except ValueError:
                            pass
                        else:
                            # Read the schedule starting from the row at
                            # the starting_index index.
                            for row in (
                                itertools.islice(
                                    reversed(times),
                                    len(times) - ending_index,
                                    None
                                )
                                if backwards else
                                itertools.islice(
                                    times,
                                    starting_index,
                                    None
                                )
                            ):
                                # Add the edge.
                                d = datetime.datetime.combine(
                                    date_arrive
                                    if backwards else
                                    date_depart,
                                    MIDNIGHT
                                ) + row[0].time
                                a = datetime.datetime.combine(
                                    date_arrive
                                    if backwards else
                                    date_depart,
                                    MIDNIGHT
                                ) + row[1].time
                                heapq.heappush(
                                    edges_heap,
                                    EdgeHeapQKey(
                                        datetime.datetime.max - d
                                        if backwards else
                                        a - datetime.datetime.min,
                                        Weight(
                                            d,
                                            a,
                                            "Take Route " +
                                            schedule.route + "." +
                                            (
                                                " Signal driver to stop."
                                                if row[1].soft
                                                else ""
                                            )
                                        )
                                    )
                                )
                                if backwards:
                                    if a < first_arrival:
                                        first_arrival = a
                                elif d > last_departure:
                                    last_departure = d
                                days_without_edges = 0
                if backwards:
                    # Decrement the day and continue.
                    try:
                        date_arrive -= ONE_DAY
                    except OverflowError:
                        date_overflowed = True
                    else:
                        timedelta_arrive = ONE_DAY
                else:
                    # Increment the day and continue.
                    try:
                        date_depart += ONE_DAY
                    except OverflowError:
                        date_overflowed = True
                    else:
                        if timedelta_depart < ONE_DAY:
                            timedelta_depart = JUST_BEFORE_MIDNIGHT
                        else:
                            timedelta_depart -= ONE_DAY
                # Check again whether more edges need to be computed.
                continue
            if edges_heap:
                e = heapq.heappop(edges_heap).edge
                if datetime_depart < e.datetime_depart \
                and e.datetime_arrive < datetime_arrive:
                    yield e
                else:
                    break
            else:
                break
    @classmethod
    def get_pickup(cls, from_node, datetime_depart):
        date_depart, timedelta_depart = timedelta_after_midnight(
            datetime_depart
        )
        # To account for schedules that run past midnight and from the previous
        # day, we start our search in the previous day but with one day added
        # to the timedelta.
        try:
            date_depart -= ONE_DAY
        except OverflowError:
            pass
        else:
            timedelta_depart += ONE_DAY
        last_departure = datetime.datetime.min
        # Use a priority queue as a buffer for edges. This allows us to make
        # sure that we have scanned all the schedules at least one day ahead
        # before we determine which is the soonest trip and yield it.
        edges_heap = []
        date_overflowed = False
        days_without_edges = 0
        # Yield edges until we hit the maximum date.
        while True:
            # If the departure times of the edges in the buffer do not span at
            # least a day, compute more edges. If no departures are seen in
            # seven days, just stop; there will not be any more because the
            # schedules repeat every week.
            if days_without_edges < 7 and (
                not edges_heap or
                (last_departure - edges_heap[0].edge.datetime_depart) < ONE_DAY
            ) and not date_overflowed:
                days_without_edges += 1
                for schedule in schedule_by_day[date_depart.weekday()]:
                    for from_node_index \
                        in schedule.get_column_indices(from_node):
                        # Filter out the rows where the vehicle will not stop
                        # and pick up passengers at from_node.
                        # Recall that row[-1] is guaranteed not to be None by
                        # parse_schedule_row in pickle_nyu.py.
                        # len(row) - 1 will be used later to get the name of
                        # the final stop in the trip.
                        times = [
                            (row[from_node_index], row[-1], len(row) - 1)
                            for row in schedule.other_rows
                            if from_node_index < len(row) - 1
                            and row[from_node_index] is not None
                            and row[from_node_index].pickup
                        ]
                        # Find the first row in the schedule where the
                        # departure time is greater than timedelta_depart. We
                        # only want to look at this row and the rows in the
                        # schedule that are below this row.
                        try:
                            starting_index = first_greater_than(
                                times,
                                timedelta_depart,
                                lambda x: x[0].time
                            )
                        except ValueError:
                            pass
                        else:
                            for row in itertools.islice(
                                times,
                                starting_index,
                                None
                            ):
                                # Add the edge.
                                d = datetime.datetime.combine(
                                    date_depart,
                                    MIDNIGHT
                                ) + row[0].time
                                a = datetime.datetime.combine(
                                    date_depart,
                                    MIDNIGHT
                                ) + row[1].time
                                heapq.heappush(
                                    edges_heap,
                                    EdgeHeapQKey(
                                        a - datetime.datetime.min,
                                        WeightedEdge(
                                            datetime_depart=d,
                                            datetime_arrive=a,
                                            human_readable_instruction=(
                                                "Take Route " +
                                                schedule.route + "." +
                                                (
                                                    " Signal driver to stop."
                                                    if row[1].soft
                                                    else ""
                                                )
                                            ),
                                            from_node=from_node,
                                            to_node=schedule.header_row[row[2]]
                                        )
                                    )
                                )
                                if d > last_departure:
                                    last_departure = d
                                days_without_edges = 0
                # Increment the day and continue.
                try:
                    date_depart += ONE_DAY
                except OverflowError:
                    date_overflowed = True
                else:
                    if timedelta_depart < ONE_DAY:
                        timedelta_depart = JUST_BEFORE_MIDNIGHT
                    else:
                        timedelta_depart -= ONE_DAY
                # Check again whether more edges need to be computed.
                continue
            if edges_heap:
                yield heapq.heappop(edges_heap).edge
            else:
                break
