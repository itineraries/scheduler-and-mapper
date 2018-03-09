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
        yielded in reverse chronological order. Otherwise, they are yielded in
        chronological order.
        
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
