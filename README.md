# Scheduler and Mapper
This code is responsible for parsing schedule data and finding itineraries.

## Install dependencies
1. Install the following Python libraries: `attrs python-dateutil keyring`
2. Get a [Bing Maps API key](https://msdn.microsoft.com/library/ff428642.aspx)
   and store it with this command: `keyring set bing_maps default`
3. Clone [string-match](https://github.com/itineraries/string-match) to `..`.
4. Download `tabula-1.0.1-jar-with-dependencies.jar` from
   [tabula-java](https://github.com/tabulapdf/tabula-java/releases).

## Acquire schedules
1. Download the PDFs from NYU and update `NYU Bus Schedules.csv`.
2. Run `pickle_nyu.py`.
3. Download the
   [stops feed](https://market.mashape.com/transloc/openapi-1-2#stops)
   from the TransLoc API. Save it as `NYU_Stops.json`.
4. Run `match_stops_locations.py`. If it says to check a stop in the overrides
   file, then update `Stop Location Overrides.csv`.
5. Run `pickle_walking.py`.

## Get an itinerary
Run `get_itinerary.py --help` to see options for getting an itinerary.
