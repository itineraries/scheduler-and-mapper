import datetime, json, keyring, os, pickle, requests
from agency_walking import AgencyWalking
from common import Weight
import stops
import time

try:
    _apikey = os.environ["GMAPS_DISTANCE_MATRIX_KEY"]
except KeyError:
    _apikey = keyring.get_password("google_maps", "distance_matrix")

ONE_MINUTE = datetime.timedelta(minutes=1)

class AgencyWalkingDynamic(AgencyWalking):
        edges = {}
        stop_coords = list(stops.geo_str_to_name.keys())
        stop_names = stops.names_sorted
        def display_dict(cls):
                ##this is just a tester method to make sure the dictionary is correct
                ##not to be used in production
                for k,v in cls.edges.items():
                        print("Origin: {} Destination: {} Distance: {} Travel Time: {} ".format(k[0], k[1], v[0], v[1]))
        @staticmethod
        def matrix_api_call(origins, destinations):
                api_key = _apikey
                # Google Distance Matrix base URL to which all other parameters are attached
                base_url = 'https://maps.googleapis.com/maps/api/distancematrix/json?'
                if (len(origins) >= 25 and len(destinations) >= 25) or ((len(origins) + len(destinations)) > 100):
                    print("Too many origins/destinations")
                    return
                payload= {
                                'units': 'imperial',
                                'region': 'us', ##It's most likely that the location is in the US so we give it precedence
                                'origins' : '|'.join(origins),
                                'destinations' : '|'.join(destinations),
                                'mode' : 'walking',
                                'api_key' : api_key
                }
                current_delay = 0.1  # Set the initial retry delay to 100ms.
                max_delay = 600  # Set the maximum retry delay to 10 minutes.
                while True:
                    try:
                        r = requests.get(base_url, params = payload)
                    except IOError:
                        pass
                    else:
                        matrix = json.loads(r.text)
                        if matrix['status'] == 'OK':
                            return matrix
                        elif matrix['status'] != 'UNKNOWN_ERROR':
                            # Many API errors cannot be fixed by a retry, e.g. INVALID_REQUEST or
                            # ZERO_RESULTS. There is no point retrying these requests.
                            print(matrix['error_message']) #TODO send errors some place so we are notified

                    if current_delay > max_delay:
                        print('Too many retry attempts.')
                    print ('Waiting' + str(current_delay) + 'seconds before retrying.')
                    time.sleep(current_delay)
                    current_delay *= 2  # Increase the delay each time we retry.


        @classmethod
        def use_origin_destination(cls,origin, destination):
                #This is from the origin to bus stops
                new_stops_origin = []
                new_stops_dest = []
                for stop in cls.stop_names: ##don't need to make an api call for edges already in the dict
                    if (origin, stop) not in cls.edges:
                        new_stops_origin.append(stop)
                    if (stop, destination) not in cls.edges:
                        new_stops_dest.append(stop)

                if destination not in stops.name_to_point and (origin, destination) not in cls.edges: ## have the origin route to the destination too, but only add if it's not already a stop
                    new_stops_origin.append(destination)
                #This is from the origin to bus stops
                #if origin isn't a bus stop and every edge for this stop is already cached 
                #we wont make an api request   
                if origin not in stops.name_to_point and len(new_stops_origin) != 0: 
                        origin_from_nodes = [origin]
                        origin_to_nodes = new_stops_origin
                        orig = cls.matrix_api_call(origin_from_nodes, origin_to_nodes)
                        if orig:
                            for to_node_i, to_node in enumerate(orig['destination_addresses']): ## bus stops are destinations
                                    row = orig['rows'][0]
                                    cell = row['elements'][to_node_i]
                                    from_node = origin
                                    to_node_name = origin_to_nodes[to_node_i] ##we have to get the bus stop name

                                    if cell['status'] == 'OK':
                                            key = (from_node, to_node_name)
                                            ##the distance is being sent in text form as that is to be read by humans while the duration is sent
                                            ##by value as it is only considered by the computer
                                            ##I think I will change this though to just send cell['distance'] and cell['duration']
                                            cls.edges[key] = (cell['distance']['text'], cell['duration']['value'], to_node)
                                    else:
                                            print("Error with edge")

                #This is from the bus stops to destination
                if destination not in stops.name_to_point and len(new_stops_dest) != 0:
                        dest_from_nodes = new_stops_dest
                        dest_to_nodes = [destination]
                        dest = cls.matrix_api_call(dest_from_nodes, dest_to_nodes)
                        if dest:
                            for from_node_i, from_node in enumerate(dest['origin_addresses']):
                                    row = dest['rows'][from_node_i]
                                    cell = row['elements'][0]
                                    to_node = destination
                                    from_node_name = dest_from_nodes[from_node_i]
                                    if cell['status'] == 'OK':
                                            key = (from_node_name, destination)
                                            ##the distance is being sent in text form as that is to be read by humans while the duration is sent
                                            ##by value as it is only considered by the computer
                                            ##I think I will change this though to just send cell['distance'] and cell['duration']
                                            cls.edges[key] = (cell['distance']['text'], cell['duration']['value'], dest['destination_addresses'][0])
                                    else:
                                            print("Error with edge")




        @classmethod
        def get_edge(cls, from_node, to_node,
                datetime_depart=datetime.datetime.min,
                datetime_arrive=datetime.datetime.max,
                consecutive_agency=None
        ):
                key = (from_node, to_node)

                if consecutive_agency is None or not issubclass(consecutive_agency, AgencyWalking):
                        ##check consecutive agency we don't want to repeat agencies
                        #the nodes must be in the dictionary otherwise we can't do anything.
                        try:
                                distance, seconds, address = cls.edges[key]
                        except KeyError:
                                    return
                        if seconds < cls.max_seconds: # the distance between the two nodes isn't impossible
                            travel_duration = datetime.timedelta(seconds=seconds)
                            if datetime_depart == datetime.datetime.min and \
                               datetime_arrive != datetime.datetime.max: ##arrival time passed in
                                    if datetime_arrive > datetime.datetime.min + travel_duration: ##the arrival time isn't impossible
                                            datetime_depart = datetime_arrive - travel_duration
                                            while True:
                                                    yield Weight(
                                                        datetime_depart,
                                                        datetime_arrive,
                                                        human_readable_instruction="Walk " + distance + " to " + address + "."
                                                    )
                                                    if datetime_depart - datetime.datetime.min <= ONE_MINUTE:
                                                        break
                                                    datetime_depart -= ONE_MINUTE
                                                    datetime_arrive -= ONE_MINUTE
                            else:
                                    # Yield the earliest trip and then go forward in time.
                                    stop = datetime_arrive
                                    if datetime_depart < \
                                        datetime.datetime.max - travel_duration and \
                                        datetime_arrive > \
                                        datetime.datetime.min + travel_duration:
                                        datetime_arrive = datetime_depart + travel_duration
                                        while True:
                                            yield Weight(
                                                datetime_depart,
                                                datetime_arrive,
                                                human_readable_instruction="Walk " + distance + " to " + address + "."
                                            )
                                            if datetime.datetime.max - datetime_arrive <= ONE_MINUTE:
                                                break
                                            datetime_depart += ONE_MINUTE
                                            datetime_arrive += ONE_MINUTE
if __name__ == "__main__":
    print(_apikey)
    bus_st = "6 MetroTech"
    origin = "Kimmel Center For University Life"
    dest = "5 MetroTech"
    bus_st_2 = "715 Broadway"
    s = AgencyWalkingDynamic()
    n = 10
    sleep_time = 10
    for x in range(0,40):
        # s.use_origin_destination(origin, bus_st)
        
        # s.use_origin_destination(bus_st, dest)
        
        s.use_origin_destination(origin, dest)
        
        # s.use_origin_destination(bus_st_2, bus_st)

        print("Attempt ", x)

        print("Origin to bus_st: ")
        for e in s.get_edge(origin ,bus_st, datetime.datetime.now()):
            print(e.human_readable_instruction)
            break
        print("origin to dest: " )
        for e in s.get_edge(origin ,dest, datetime.datetime.now()):
            print(e.human_readable_instruction)
            break
        print("bus_st to dest: " )
        for e in s.get_edge(bus_st ,dest, datetime.datetime.now()):
            print(e.human_readable_instruction)
            break

        # print("THIS SHOULDN'T WORK bus_st2 to bus_st: " )
        # for e in s.get_edge(bus_st_2 ,bus_st, datetime.datetime.now()):       
        #     print(e.human_readable_instruction)
        #     break


