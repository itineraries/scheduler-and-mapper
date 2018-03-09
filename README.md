# Scheduler and Mapper
This code is responsible for parsing schedule data and finding itineraries.

## Install dependencies
1. Install the following Python libraries: `attrs python-dateutil keyring`
2. Get a [Bing Maps API key](https://msdn.microsoft.com/library/ff428642.aspx)
   and add store it with `keyring set bing_maps default`.
3. Clone [string-match](https://github.com/itineraries/string-match) to `..`.
## Get an itinerary
Run `get_itinerary.py --help` to see options for getting an itinerary.
