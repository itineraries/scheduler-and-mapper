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

## Modify schedules (optional)
NYU publishes its bus schedules as timetables in PDF documents. If you want to
add or remove schedules or change how they are parsed, see these configuration
files.

[Click here](https://www.nyu.edu/life/travel-and-transportation/university-transportation/routes-and-schedules.html)
for more information about the NYU bus schedules and to download timetables.

### NYU Bus Schedules.csv
If you want to include more schedules, download them to this directory and add
them to this CSV. If you want to exclude schedules, remove their entries from
this file. The following sections explain each column.

#### Filename
Insert the path to the PDF with the timetable. It can be absolute, or it can be
relative to the `NYU` directory inside this directory.

#### Page
This is the page number of the page inside the PDF that the timetable is on.
For single-page PDF documents, just insert `1`. Only one page will be scanned.
If you want more pages to be scanned, add more rows to the CSV file with the
same filename but different page numbers.

#### Area (Top, Left, Bottom, Right)
Define a rectangle for in which the timetable will be scanned. The top and
bottom sides are defined as points from the top of the page. The left and right
sides are defined as points from the left edge of the page.

#### Column Boundaries
If you want to change the column detection method for any schedule, modify its
entry appropriately in this file. These are the available options:

 - `auto`: `tabula-java` will automatically decide the column detection method.
 - `stream`: `tabula-java` will look for vertically contiguous regions with no
   text between columns.
 - `lattice`: `tabula-java` will look for lines that are drawn between columns.
 - A string of comma-separated integers in base-10: the columns will be
   separated at these predefined distances, in points, from the left edge of
   the page. Note that because the CSV file format uses commas to delimit
   columns, you must surround this string with quotation marks if you are
   editing the CSV file in a text editor.

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
