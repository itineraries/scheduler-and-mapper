#!/usr/bin/env python3
'''
This module implements a uniform cost search.
'''
import attr, collections, datetime, heapq, pickle
import stops
from agency_common import Agency, Direction

class ItineraryNotPossible(Exception):
    '''
    This exception is raised when find_itinerary is unable to find an itinerary
    with the given arguments.
    '''
@attr.s(frozen=True)
class WeightedEdge(Agency.Weight):
    # The agency that provided this edge
    agency = attr.ib(
        default=None,
        validator=attr.validators.optional(
            lambda self, attribute, value: issubclass(value, Agency)
        )
    )
    # The node to which this edge connects
    neighbor_node = attr.ib(default=None)
@attr.s
class PreviousNode:
    edge = attr.ib(
        default=WeightedEdge(),
        validator=attr.validators.instance_of(WeightedEdge)
    )
    num_stops_to_node = attr.ib(
        default=0,
        validator=attr.validators.instance_of(int)
    )
def weighted_edges(
    agencies,
    known_node,
    datetime_trip,
    depart,
    consecutive_agency,
    extra_nodes=frozenset(),
    disallowed_edges=()
):
    '''
    Generates directed, weighted edges from known_node.
    
    The weight is the time delta between datetime_trip and the time
    that you would arrive at the ending node if you took this edge.
    
    Arguments:
        agencies:
            an iterable of subclasses of Agency
        known_node:
            the starting node
        datetime_trip:
            the datetime that the user arrives at known_node and begins
            waiting
        depart:
            same as the argument of the same neighbor_node for find_trip
        consecutive_agency:
            the agency that provided the edge leading to from_node if
            depart is True or to_node otherwise
        extra_nodes:
            a set or frozenset of nodes to consider in addition to the
            nodes that are already in stops.neighbor_node_to_point.keys()
        disallowed_edges:
            a container that supports the membership test operations and that
            contains instances of WeightedEdge, exact matches of which should
            not be yielded
    Yields:
        A WeightedEdge object
    '''
    for node in (stops.name_to_point.keys() | extra_nodes) - {known_node}:
        for agency in agencies:
            try:
                e = next(
                    # depart = True: Only process edges from known_node.
                    # depart = False: Only process edges to known_node.
                    agency.get_edge(
                        known_node,
                        node,
                        datetime_depart=datetime_trip,
                        consecutive_agency=consecutive_agency
                    ) if depart else agency.get_edge(
                        node,
                        known_node,
                        datetime_arrive=datetime_trip,
                        consecutive_agency=consecutive_agency
                    )
                )
            except StopIteration:
                pass
            else:
                result = WeightedEdge(
                    agency=agency,
                    datetime_depart=e.datetime_depart,
                    datetime_arrive=e.datetime_arrive,
                    human_readable_instruction=e.human_readable_instruction,
                    neighbor_node=node
                )
                if result not in disallowed_edges:
                    yield result
def find_itinerary(
    agencies,
    origin,
    destination,
    trip_datetime,
    depart,
    disallowed_edges=()
):
    '''
    Finds an itinerary that will take the user from the origin to the
    destination before or after the given time. If there is no path from the
    origin to the destination, then ItineraryNotPossible is raised.
    
    The origin and destination are strings. Each must cause at least one agency
    to yield edges, or ItineraryNotPossible will be raised. Other than that,
    there are no restrictions. The strings may be the neighbor_nodes of bus
    stops. They might be street addresses. They might be the neighbor_nodes of
    buildings.
    
    The origin and destination must not be equal. If they are equal, then
    ItineraryNotPossible will be raised.
    
    Arguments:
        agencies:
            An iterable of subclasses of Agency
        origin:
            A string that represents the starting location of the itinerary
        destination:
            A string that represents the ending location of the itinerary
        trip_datetime:
            A datetime; see the explanation for depart
        depart:
            If True, the itinerary has the user depart after trip_datetime.
            If False, the itinerary has the user arrive before trip_datetime.
        disallowed_edges:
            a container that supports the membership test operations and that
            contains instances of WeightedEdge, exact matches of which should
            not be yielded
    Returns:
        The itinerary is returned as a list of Direction objects.
    '''
    visit_queue = []
    extra_nodes = {origin, destination}
    # Pass the origin and destination to the agencies.
    for agency in agencies:
        agency.use_origin_destination(origin, destination)
    # Assign to every node a tentative distance value.
    # Set it to zero for our initial node and to infinity for the rest.
    previous_node = collections.defaultdict(PreviousNode)
    # Set the initial node as current. Mark all other nodes unvisited.
    if depart:
        previous_node[origin] = PreviousNode(
            WeightedEdge(datetime_arrive=trip_datetime)
        )
        heapq.heappush(
            visit_queue,
            (datetime.datetime.min, datetime.timedelta(0), 0, origin)
        )
        stop_algorithm = destination
    else:
        previous_node[destination] = PreviousNode(
            WeightedEdge(datetime_depart=trip_datetime)
        )
        heapq.heappush(
            visit_queue,
            (datetime.timedelta(0), datetime.datetime.min, 0, destination)
        )
        stop_algorithm = origin
    # Visit each node at most once.
    visited = set()
    while visit_queue:
        current_node = heapq.heappop(visit_queue)[-1]
        if current_node not in visited:
            # Mark the current node as visited.
            # A visited node will never be checked again.
            visited.add(current_node)
            # For the current node, consider all of its unvisited neighbors
            # and calculate their tentative distances. Compare the newly
            # calculated tentative distance to the currently assigned value
            # and assign the smaller one.
            for e in weighted_edges(
                agencies,
                current_node,
                previous_node[current_node].edge.datetime_arrive
                if depart else
                previous_node[current_node].edge.datetime_depart,
                depart,
                previous_node[current_node].edge.agency,
                extra_nodes,
                disallowed_edges
            ):
                num_stops_to_node_new = previous_node[
                    current_node
                ].num_stops_to_node + 1
                n = previous_node[e.neighbor_node]
                if depart:
                    neighbor_distance_old = (
                        n.edge.datetime_arrive,
                        n.num_stops_to_node,
                        datetime.datetime.max - n.edge.datetime_depart
                    )
                    neighbor_distance_new = (
                        e.datetime_arrive,
                        num_stops_to_node_new,
                        datetime.datetime.max - e.datetime_depart
                    )
                else:
                    neighbor_distance_old = (
                        datetime.datetime.max - n.edge.datetime_depart,
                        n.num_stops_to_node,
                        n.edge.datetime_arrive
                    )
                    neighbor_distance_new = (
                        datetime.datetime.max - e.datetime_depart,
                        num_stops_to_node_new,
                        e.datetime_arrive
                    )
                if neighbor_distance_new < neighbor_distance_old:
                    previous_node[e.neighbor_node] = PreviousNode(
                        WeightedEdge(
                            agency=e.agency,
                            datetime_arrive=e.datetime_arrive,
                            datetime_depart=e.datetime_depart,
                            human_readable_instruction=
                                e.human_readable_instruction,
                            neighbor_node=current_node,
                        ),
                        num_stops_to_node=num_stops_to_node_new
                    )
                    heapq.heappush(
                        visit_queue,
                        neighbor_distance_new + (e.neighbor_node,)
                    )
            # If the target node has been visited, then break.
            if current_node == stop_algorithm:
                break
    # If the destination node has been marked visited (when planning a
    # route between two specific nodes) or if the smallest tentative
    # distance among the nodes in the unvisited set is infinity (when
    # planning a complete traversal; occurs when there is no connection
    # between the initial node and remaining unvisited nodes), then stop.
    if previous_node[
        destination if depart else origin
    ].edge.neighbor_node is None:
        raise ItineraryNotPossible
        return None
    # Prune away the departure from the destination.
    # Retrace our path from the destination back to the origin.
    # Compile a list showing the stops that we made on the way.
    itinerary = []
    if depart:
        current_node = destination
        while current_node is not None:
            n = previous_node[current_node]
            itinerary.append(
                Direction(
                    from_node=n.edge.neighbor_node,
                    datetime_depart=n.edge.datetime_depart,
                    human_readable_instruction=
                        n.edge.human_readable_instruction,
                    to_node=current_node,
                    datetime_arrive=n.edge.datetime_arrive
                )
            )
            current_node = n.edge.neighbor_node
        itinerary = itinerary[-2::-1]
    else:
        current_node = origin
        while current_node is not None:
            n = previous_node[current_node]
            itinerary.append(
                Direction(
                    from_node=current_node,
                    datetime_depart=n.edge.datetime_depart,
                    human_readable_instruction=
                        n.edge.human_readable_instruction,
                    to_node=n.edge.neighbor_node,
                    datetime_arrive=n.edge.datetime_arrive
                )
            )
            current_node = n.edge.neighbor_node
        itinerary.pop()
    # We are done.
    return itinerary
