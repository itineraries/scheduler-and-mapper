import datetime, json, keyring, os, pickle, requests
from agency_walking import AgencyWalking
import stops

try:
    _apikey = os.environ["GMAPS_DISTANCE_MATRIX_KEY"]
except KeyError:
    _apikey = keyring.get_password("google_maps", "default")

ONE_MINUTE = datetime.timedelta(minutes=1)

class AgencyWalkingDynamic(AgencyWalking):
        edges = {}
        stops = list(stops.geo_str_to_name.keys())

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
                r = requests.get(base_url, params = payload)
                if r.status_code != 200:
                                print('HTTP status code {} received, program terminated.'.format(r.status_code))
                else:
                        try:
                                # Try/catch block should capture the problems when loading JSON data,
                                # such as when JSON is broken.
                                matrix = json.loads(r.text)
                                return matrix
                        except ValueError:
                                print('Error while parsing JSON response, program terminated.')




        @classmethod
        def use_origin_destination(cls,origin, destination):
                #This is from the origin to bus stops
                if origin not in stops.name_to_point:
                        origin_from_nodes = [origin]
                        origin_to_nodes = cls.stops
                        orig = cls.matrix_api_call(origin_from_nodes, origin_to_nodes)
                        if orig:
                            for to_node_i, to_node in enumerate(orig['destination_addresses']): ## bus stops are destinations
                                    row = orig['rows'][0]
                                    cell = row['elements'][to_node_i]
                                    from_node = origin
                                    to_node_name = stops.geo_str_to_name[cls.stops[to_node_i]] ##we have to get the bus stop name
                                    if cell['status'] == 'OK':
                                            key = (from_node, to_node_name)
                                            ##the distance is being sent in text form as that is to be read by humans while the duration is sent
                                            ##by value as it is only considered by the computer
                                            ##I think I will change this though to just send cell['distance'] and cell['duration']
                                            cls.edges[key] = (cell['distance']['text'], cell['duration']['value'], orig['origin_addresses'][0])
                                    else:
                                            print("Error with edge")

                #This is from the bus stops to destination
                if destination not in stops.name_to_point:
                        dest_from_nodes = cls.stops
                        dest_to_nodes = [destination]
                        dest = cls.matrix_api_call(dest_from_nodes, dest_to_nodes)
                        if dest:
                            for from_node_i, from_node in enumerate(dest['origin_addresses']):
                                    row = dest['rows'][from_node_i]
                                    cell = row['elements'][0]
                                    to_node = destination
                                    from_node_name = stops.geo_str_to_name[cls.stops[from_node_i]]
                                    if cell['status'] == 'OK':
                                            key = (from_node_name, to_node)
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
                                if seconds < cls.max_seconds: # the distance between the two nodes isn't impossible
                                        travel_duration = datetime.timedelta(seconds=seconds)
                                        if datetime_depart == datetime.datetime.min and \
                                           datetime_arrive != datetime.datetime.max: ##arrival time passed in
                                                if datetime_arrive > datetime.datetime.min + travel_duration: ##the arrival time isn't impossible
                                                        datetime_depart = datetime_arrive - travel_duration
                                                        while True:
                                                                yield cls.UnweightedEdge(
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
                                                        yield cls.UnweightedEdge(
                                                            datetime_depart,
                                                            datetime_arrive,
                                                            human_readable_instruction="Walk " + distance + " to " + address + "."
                                                        )
                                                        if datetime.datetime.max - datetime_arrive <= ONE_MINUTE:
                                                            break
                                                        datetime_depart += ONE_MINUTE
                                                        datetime_arrive += ONE_MINUTE
                        except KeyError:
                                    return
if __name__ == "__main__":
        destination = "6 MetroTech"
        origin = "Kimmel Center For University Life"
        s = AgencyWalkingDynamic()
        s.use_origin_destination(origin, origin)
        s.display_dict()
        s.get_edge(origin, "715 Broadway" , datetime.datetime.now())
        for e in s.get_edge("715 Broadway", origin , datetime.datetime.now()):
               print(e.human_readable_instruction)
               break

