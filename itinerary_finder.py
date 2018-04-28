#!/usr/bin/env python3
'''
This module implements a uniform cost search.
'''
import attr, collections, datetime, heapq, itertools
import stops
from agency_common import Agency
from common import WeightedEdge

class ItineraryNotPossible(Exception):
    '''
    This exception is raised when find_itinerary is unable to find an itinerary
    with the given arguments.
    '''
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
    extra_nodes=frozenset()
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
    Yields:
        A WeightedEdge object
    '''
    for node in (stops.name_to_point.keys() | extra_nodes) - {known_node}:
        for agency in agencies:
            try:
                weight = next(
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
                edge = WeightedEdge(
                    agency=agency,
                    datetime_depart=weight.datetime_depart,
                    datetime_arrive=weight.datetime_arrive,
                    human_readable_instruction=weight.human_readable_instruction,
                    intermediate_nodes=weight.intermediate_nodes,
                    from_node=node if depart else known_node,
                    to_node=known_node if depart else node
                )
                yield edge
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
            # For the current node, consider all of its unvisited neighbors.
            previous_node_current_node_edge = previous_node[current_node].edge
            for edge in weighted_edges(
                agencies,
                current_node,
                previous_node_current_node_edge.datetime_arrive
                if depart else
                previous_node_current_node_edge.datetime_depart,
                depart,
                previous_node_current_node_edge.agency,
                extra_nodes
            ):
                neighbor_node = edge.from_node if depart else edge.to_node
                num_stops_to_node_new = previous_node[
                    current_node
                ].num_stops_to_node + 1
                n = previous_node[neighbor_node]
                # Calculate the unvisited neighbor's tentative distance.
                if depart:
                    neighbor_distance_old = (
                        n.edge.datetime_arrive,
                        n.num_stops_to_node,
                        datetime.datetime.max - n.edge.datetime_depart
                    )
                    neighbor_distance_new = (
                        edge.datetime_arrive,
                        num_stops_to_node_new,
                        datetime.datetime.max - edge.datetime_depart
                    )
                else:
                    neighbor_distance_old = (
                        datetime.datetime.max - n.edge.datetime_depart,
                        n.num_stops_to_node,
                        n.edge.datetime_arrive
                    )
                    neighbor_distance_new = (
                        datetime.datetime.max - edge.datetime_depart,
                        num_stops_to_node_new,
                        edge.datetime_arrive
                    )
                # Compare the newly calculated tentative distance to the
                # currently assigned value and assign the smaller one.
                if neighbor_distance_new < neighbor_distance_old:
                    direction = WeightedEdge(
                        agency=edge.agency,
                        datetime_arrive=edge.datetime_arrive,
                        datetime_depart=edge.datetime_depart,
                        human_readable_instruction=
                            edge.human_readable_instruction,
                        intermediate_nodes=edge.intermediate_nodes,
                        from_node=
                            current_node if depart else edge.to_node,
                        to_node=edge.from_node if depart else current_node
                    )
                    if direction not in disallowed_edges:
                        previous_node[neighbor_node] = PreviousNode(
                            direction,
                            num_stops_to_node=num_stops_to_node_new
                        )
                        heapq.heappush(
                            visit_queue,
                            neighbor_distance_new + (neighbor_node,)
                        )
            # If the target node has been visited, then break.
            if current_node == stop_algorithm:
                break
    # If the destination node has been marked visited (when planning a
    # route between two specific nodes) or if the smallest tentative
    # distance among the nodes in the unvisited set is infinity (when
    # planning a complete traversal; occurs when there is no connection
    # between the initial node and remaining unvisited nodes), then stop.
    if (
        previous_node[destination].edge.from_node
        if depart else
        previous_node[origin].edge.to_node
    ) is None:
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
            itinerary.append(n.edge)
            current_node = n.edge.from_node
        itinerary = itinerary[-2::-1]
    else:
        current_node = origin
        while current_node is not None:
            n = previous_node[current_node]
            itinerary.append(n.edge)
            current_node = n.edge.to_node
        itinerary.pop()
    # We are done.
    return itinerary
def find_itineraries(
    agencies_to_vary,
    *args,
    max_count=None,
    disallowed_edges=None,
    **kwargs
):
    '''
    Finds multiple itineraries instead of just one. This is a generator; the
    itineraries are yielded. Each itinerary has one or more different edges
    than the others. The agency of every varied edge will be in
    agencies_to_vary. A maximum of max_count itineraries will be yielded.
    
    Arguments:
        agencies_to_vary:
            A container that supports membership test operations and that
            contains subclasses of Agency. The yielded itineraries will differ
            in edges whose agencies are in this container. Some or all agencies
            will make a difference.
        max_count:
            An integer or None. No more than this number of itineraries will be
            yielded. If this argument is None, then there will be no limit.
        disallowed_edges:
            A set or frozenset that contains instances of WeightedEdge, exact
            matches of which will not be in any of the yielded itineraries
        *args and **kwargs:
            All other arguments will be forwarded to find_itinerary.
    '''
    # Handle the maximum number of itineraries here while handling the rest of
    # the computations in a recursive call.
    if max_count is not None:
        for itinerary in find_itineraries(
            agencies_to_vary,
            *args,
            max_count=None,
            disallowed_edges=disallowed_edges,
            **kwargs
        ):
            # We could use itertools.islice, but this is simpler.
            max_count -= 1
            if max_count < 0:
                return
            yield itinerary
    # Find an itinerary normally.
    if disallowed_edges is None:
        disallowed_edges = frozenset()
    try:
        itinerary = find_itinerary(
            *args,
            disallowed_edges=disallowed_edges,
            **kwargs
        )
    except ItineraryNotPossible:
        return
    else:
        yield itinerary
    # Find edges whose agencies are in agencies_to_vary.
    edges_to_disallow = {
        edge for edge in itinerary if edge.agency in agencies_to_vary
    }
    # Recursively find more itineraries with different combinations of
    # disallowed edges.
    generators = collections.deque()
    for i in range(1, len(edges_to_disallow) + 1):
        for de_combo in itertools.combinations(edges_to_disallow, i):
            generators.append(
                find_itineraries(
                    agencies_to_vary,
                    *args,
                    max_count=None,
                    disallowed_edges=disallowed_edges.union(de_combo),
                    **kwargs
                )
            )
    # Yield itineraries from the generators, breadth-first.
    while generators:
        for generator in generators:
            try:
                yield next(generator)
            except StopIteration:
                generators.remove(generator)
                break
