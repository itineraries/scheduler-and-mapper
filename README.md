# Scheduler and Mapper
This code is responsible for parsing schedule data and finding itineraries.

## Install dependencies
1. Install Python dependencies by running `pip install -r requirements.txt`.
2. Get a [Bing Maps API key](https://msdn.microsoft.com/library/ff428642.aspx)
   and store it with this command: `keyring set bing_maps default`
3. Get a [Google Maps Distance Matrix API key](https://developers.google.com/maps/documentation/distance-matrix/)
   and either store it in an environment variable called
   `GMAPS_DISTANCE_MATRIX_KEY` or store it with this command:
   `keyring set google_maps distance_matrix`
4. Clone [string-match](https://github.com/itineraries/string-match) to `..`,
   switch to `../string-match`, run `make libmatcher.so`, and switch back here.
5. Download `tabula-1.0.1-jar-with-dependencies.jar` from
   [tabula-java](https://github.com/tabulapdf/tabula-java/releases).

## Build schedules
1. Run `pickle_nyu.py`.
2. Download the
   [stops feed](https://market.mashape.com/transloc/openapi-1-2#stops)
   from the TransLoc API. Save it as `NYU_Stops.json`.
3. Run `match_stops_locations.py`. If it says to check a stop in the overrides
   file, then update `Stop Location Overrides.csv`.
4. Run `pickle_walking_static.py`.

## Modify schedules (optional)
NYU publishes its bus schedules as timetables in Google Sheets sheets. If you
want to add or remove schedules or change how they are parsed, see these
configuration files.

[Click here](https://www.nyu.edu/life/travel-and-transportation/university-transportation/routes-and-schedules.html)
for more information about the NYU bus schedules and to download timetables.

### NYU Bus Schedules.csv
If you want to include more schedules, download them to this directory and add
them to this CSV. If you want to exclude schedules, remove their entries from
this file. The following sections explain each column.

#### Key
Extract the workbook key from the workbook URL. It is usually right after
`/spreadsheets/d/`. For example, given this URL:

    https://docs.google.com/spreadsheets/d/1ri820ZdZNSj0nxnaCfzaczsjY0ALORGRMnUXt23QMNE/edit#gid=1304245022

The workbook key is `1ri820ZdZNSj0nxnaCfzaczsjY0ALORGRMnUXt23QMNE`.

#### GID
Extract the worksheet GID from the workbook URL. It is usually right after
`#gid=`. For example, given the same URL as above, the worksheet GID is
`1304245022`.

#### Filename Override
When Google Drive exports a worksheet from Google Sheets, the filename is
`[Name of Workbook] - [Name of Worksheet].csv`. If the name of the workbook
does not in the format of `Route [Route] Schedule` or `Route [Route]
Schedules` or the name of the worksheet does not contain the days of the week,
then you must override the filename to contain the route and the days of the
week.

### NYU Bus Stop Replacements.csv
When the names of the bus stops are taken from the header rows of the
timetables, they undergo some string manipulation in an attempt to rectify some
instances where the same stop is given different names on different timetables.
One of the operations is a simple find-and-replace. Each instance of each
string in the **Find** column will be replaced with the corresponding string in
the **Replace** column.

### Stop Location Overrides.csv
You only need to modify this file if `match_stops_locations.py` prompts you to
check one or more stops in the "overrides file." If it cannot match the name of
a bus stop from the timetables to the name of a bus stop in the TransLoc API,
it will list that stop here. The names from the timetables are in the **From
PDFs** column, and the names from the API are in the **From API** column. The
geographic coordinates from the API are in the **Latitude Guess** and
**Longitude Guess** columns. Essentially, all that you need to do is specify
the correct geographic coordinates of each stop in the **Latitude** and
**Longitude** columns.

### Driving Time Overrides.csv
You only need to modify this file if `pickle_nyu.py` prompts you to. For each
row, all that you need to do is specify in the **Minutes** column how long it
takes, in minutes, to drive from the location in the **From** column to the
location in the **To** column.

## Get an itinerary
Run `get_itinerary.py --help` to see options for getting an itinerary.
