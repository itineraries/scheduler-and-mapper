#!/usr/bin/env python3
import abc, attr, datetime

class Agency(abc.ABC):
    @attr.s
    class UnweightedEdge:
        # datetime of departure from from_node
        datetime_depart = attr.ib()
        # datetime of arrival at to_node
        datetime_arrive = attr.ib()
        # A string of a human-readable instruction
        human_readable_instruction = attr.ib()
    @classmethod
    def add_arguments(cls, arg_parser_add_argument):
        '''
        Call this function before parsing command line arguments. This function
        may add additional arguments to be parsed. By default, this function
        does nothing; subclasses may override it.
        
        Arguments:
            arg_parser_add_argument:
                The bound add_argument method of an instance of an
                argparse.ArgumentParser
        '''
    @classmethod
    def handle_parsed_arguments(cls, args_parsed):
        '''
        Call this function after parsing command line arguments. This function
        will read the parsed arguments and may make changes to class members
        based on the parsed arguments. By default, this function does nothing;
        subclasses may override it.
        
        Arguments:
            args_parsed:
                The return value of the parse_args method of the same instance
                of argparse.ArgumentParser whose add_argument method was passed
                to add_arguments
        '''
    @classmethod
    def use_origin_destination(cls, origin, destination):
        '''
        This function will use the origin and destination to optimize calls to
        get_edge. It must be called before the first call to get_edge after the
        origin or destination changes.
        '''
    @classmethod
    @abc.abstractmethod
    def get_edge(
        cls,
        from_node,
        to_node,
        datetime_depart=datetime.datetime.min,
        datetime_arrive=datetime.datetime.max,
        consecutive_agency=None
    ):
        '''
        Yields edges from from_node to to_node after datetime_depart and before
        datetime_arrive. If datetime_depart is datetime.datetime.min and
        datetime_arrive is not datetime.datetime.max, then the edges are
        yielded from the latest departure to the earliest. Otherwise, they are
        yielded from the earliest arrival to the latest.
        
        Both from_node and to_node are strings. They may be the names of bus
        stops from "Node List.txt" or from "Stop Locations.csv," or they may be
        whatever the user entered as the origin or destination. One might be a
        bus stop while the other is the origin or destination. If the agency
        cannot handle the given from_node and to_node, then get_edge should
        simply yield nothing. Another agency should handle them.
        
        This method must be overridden by a subclass. Calling it on an instance
        of this class will raise NotImplementedError.
        
        Arguments:
            from_node:
                all yielded edges will come from this node
            to_node:
                all yielded edges will go to this node
            datetime_depart:
                all yielded edges will depart at or after this datetime
            datetime_arrive:
                all yielded edges will arrive at or before this datetime
            consecutive_agency (optional):
                the agency that provided the edge leading to from_node if
                depart is True or to_node otherwise
        Yields:
            An UnweightedEdge object
        '''
        raise NotImplementedError
    @classmethod
    def get_pickup(cls, from_node, datetime_depart):
        '''
        Finds trips that depart from from_node after datetime_depart. Yields an
        edge from from_node to the trip's final destination for each trip.
        Every yielded edge's departure time is later than or equal to the last
        yielded edge's departure time.
        
        Like in get_edge, from_node is a string that may equal the name of a
        bus stop or that may be what the user entered as the origin.
        
        If this method is not overridden, then it is simply an empty generator.
        '''
        return
        yield
@attr.s
class Direction(Agency.UnweightedEdge):
    '''
    This class represents one instruction to the user within an itinerary.
    '''
    TIME_STRING = "%I:%M %p."
    from_node = attr.ib()
    to_node = attr.ib()
    def __str__(self):
        result = []
        if self.datetime_depart is not None:
            result.append("Depart from")
            result.append(str(self.from_node))
            result.append("at")
            result.append(self.datetime_depart.strftime(self.TIME_STRING))
        if self.human_readable_instruction is not None:
            result.append(str(self.human_readable_instruction))
        if self.datetime_arrive is not None:
            result.append("Arrive at")
            result.append(str(self.to_node))
            result.append("at")
            result.append(self.datetime_arrive.strftime(self.TIME_STRING))
        return " ".join(result)
