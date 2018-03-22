#!/usr/bin/env python3
import attr, heapq, pickle
from datetime import datetime, time, timedelta

class ShortestPathFinder:
    @attr.s
    class PreviousNode:
        agency = attr.ib()
        arrival_time = attr.ib()
        departure_time = attr.ib()
        human_readable_instruction = attr.ib()
        name = attr.ib()
        num_stops_to_node = attr.ib()
    @attr.s
    class WeightedEdge:
        # The agency that provided this edge
        agency = attr.ib()
        # The datetime at which the user departs before this edge
        datetime_depart = attr.ib()
        # The datetime at which the user arrives after this edge
        datetime_arrive = attr.ib()
        # A human-readable instruction to follow
        human_readable_instruction = attr.ib()
        # The node to which this edge connects
        neighbor_node = attr.ib()
    def __init__(self, nodes, agencies):
        '''
        This class essentially implements Dijkstra's algorithm.
        
        Arguments:
            edges_for_route:
                For every route, map (origin, destination) to (column of
                departure time, column of arrival time). We are assuming that
                the arrival time is the same as the departure time for all
                stops.
        '''
        self.error = "No error."
        self.nodes = set(nodes)
        self.agencies = agencies
    def weighted_edges(
        self, known_node, datetime_trip, depart, consecutive_agency
    ):
        '''
        Returns a generator for directed, weighted edges from known_node.
        The weight is the time delta between datetime_trip and the time
        that you would arrive at the ending node if you took this edge.
        
        Arguments:
            known_node:
                the starting node
            datetime_trip:
                the datetime that the user arrives at known_node and begins
                waiting
            depart:
                same as the argument of the same name for find_trip
            consecutive_agency:
                the agency that provided the edge leading to from_node if
                depart is True or to_node otherwise
        Yields:
            A WeightedEdge object
        '''
        for node in self.nodes - set((known_node,)):
            for agency in self.agencies:
                for e in (
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
                ):
                    yield self.WeightedEdge(
                        agency=agency,
                        datetime_depart=e.datetime_depart,
                        datetime_arrive=e.datetime_arrive,
                        human_readable_instruction=e.human_readable_instruction,
                        neighbor_node=node
                    )
                    # Stop after one. TODO: maybe stop after multiple.
                    break
    def find_trip(self, origin, destination, trip_datetime, depart=False):
        '''
        The arguments of this function have the same meaning as the command-line
        arguments.
        Return:
            If no trip is found, None is returned.
            If a trip is found, it is returned as a list of
            (from stop, from time, human-readable instruction, to stop, to time)
            tuples.
        '''
        # Make sure that the origin and destination are in the set of nodes.
        if origin in self.nodes and destination in self.nodes:
            # Assign to every node a tentative distance value.
            # Set it to zero for our initial node and to infinity for the rest.
            previous_node = {
                node: self.PreviousNode(
                    agency=None,
                    arrival_time=datetime.max,
                    departure_time=datetime.min,
                    human_readable_instruction=None,
                    name=None,
                    num_stops_to_node=0
                ) for node in self.nodes
            }
            # Set the initial node as current. Mark all other nodes unvisited.
            if depart:
                previous_node[origin].arrival_time = trip_datetime
                visit_queue = [(datetime.min, timedelta(0), 0, origin)]
                stop_algorithm = destination
            else:
                previous_node[destination].departure_time = trip_datetime
                visit_queue = [(timedelta(0), datetime.min, 0, destination)]
                stop_algorithm = origin
            # Visit each node at most once.
            visited = set()
            while visit_queue:
                current_node = heapq.heappop(visit_queue)[-1]
                if current_node not in visited:
                    # Mark the current node as visited.
                    # A visited node will never be checked again.
                    visited.add(current_node)
                    # For the current node, consider all of its unvisited
                    # neighbors and calculate their tentative distances.
                    # Compare the newly calculated tentative distance to the
                    # current assigned value and assign the smaller one.
                    for e in self.weighted_edges(
                        current_node,
                        previous_node[current_node].arrival_time
                        if depart else
                        previous_node[current_node].departure_time,
                        depart,
                        previous_node[current_node].agency
                    ):
                        num_stops_to_node_new = previous_node[
                            current_node
                        ].num_stops_to_node + 1
                        n = previous_node[e.neighbor_node]
                        if depart:
                            neighbor_distance_old = (
                                n.arrival_time,
                                n.num_stops_to_node,
                                datetime.max - n.departure_time
                            )
                            neighbor_distance_new = (
                                e.datetime_arrive,
                                num_stops_to_node_new,
                                datetime.max - e.datetime_depart
                            )
                        else:
                            neighbor_distance_old = (
                                datetime.max - n.departure_time,
                                n.num_stops_to_node,
                                n.arrival_time
                            )
                            neighbor_distance_new = (
                                datetime.max - e.datetime_depart,
                                num_stops_to_node_new,
                                e.datetime_arrive
                            )
                        if neighbor_distance_new < neighbor_distance_old:
                            previous_node[e.neighbor_node] = self.PreviousNode(
                                agency=e.agency,
                                arrival_time=e.datetime_arrive,
                                departure_time=e.datetime_depart,
                                human_readable_instruction=
                                    e.human_readable_instruction,
                                name=current_node,
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
            # between the initial node and remaining unvisited nodes), then
            # stop. The algorithm has finished.
            if depart:
                if previous_node[destination].name is None:
                    self.error = "This trip is not possible."
                    return None
            else:
                if previous_node[origin].name is None:
                    self.error = \
                        "This trip is not possible (reverse calculation)."
                    return None
            # Prune away the departure from the destination.
            # Retrace our path from the destination back to the origin.
            # Compile a list showing the stops that we made on the way.
            trip = []
            if depart:
                current_node = destination
                previous_node[origin].departure_time = None
                while current_node is not None:
                    n = previous_node[current_node]
                    trip.append((
                        n.name,
                        n.departure_time,
                        n.human_readable_instruction,
                        current_node,
                        n.arrival_time
                    ))
                    current_node = n.name
                trip = trip[::-1]
            else:
                current_node = origin
                previous_node[destination].arrival_time = None
                while current_node is not None:
                    n = previous_node[current_node]
                    trip.append((
                        current_node,
                        n.departure_time,
                        n.human_readable_instruction,
                        n.name,
                        n.arrival_time
                    ))
                    current_node = n.name
            # Return this list. We are done. The algorithm is finished.
            return trip
        else:
            self.error = "The origin or destination is not a known place. " \
                "Possible places include:" + "".join(
                    "\n - " + node for node in self.nodes
                )
        return None
