#!/usr/bin/env python3
# QA checklist:
# - No times in titles
# - No missing letters in titles
# - Blank cells in PDFs are still blank in the output
# - No words like "Arrival," "Arrive," "Depart," or "Departure" in titles
# - Randomly select some schedules, compare output to original PDF
import cgi, collections, copy, csv, datetime, dateutil.parser, io, itertools, \
    multiprocessing.pool, os, pickle, re, requests, subprocess, sys, \
    urllib.parse
from common import NODE_LIST_TXT, file_in_this_dir
from common_nyu import DAYS_OF_WEEK, NYU_PICKLE, NYUSchedule, NYUTime
import pickle_nyu_unwritten_times
NYU_HTML = file_in_this_dir("NYU.html")
SCHEDULES = file_in_this_dir("NYU Bus Schedules.csv")
REPLACEMENTS = file_in_this_dir("NYU Bus Stop Replacements.csv")
IGNORED_TIMES = {
    # Cells with these exact times will be treated as blank.
    datetime.time(0, 0),
    datetime.time(0, 4),
    datetime.time(0, 7),
}
ABBREVIATION_EXPANSION = {
    "&": "At",
    "at": "At",
    "N": "North",
    "E": "East",
    "S": "South",
    "W": "West",
    "NB": "Northbound",
    "EB": "Eastbound",
    "SB": "Southbound",
    "WB": "Westbound",
    "Ave": "Avenue",
    "St": "Street",
    "street": "Street",
    "Pl": "Place",
    "Metrotech": "MetroTech",
    "First": "1st",
    "Second": "2nd",
    "Third": "3rd",
}
DIRECTIONAL_WORDS = {
    "Northbound",
    "Southbound",
    "Eastbound",
    "Westbound",
    "Uptown",
    "Downtown",
    "Opposite",
}
DAYS_OF_WEEK_REVERSE = {
    "Mon": 0,
    "Tue": 1,
    "Wed": 2,
    "Thu": 3,
    "Fri": 4,
    "Sat": 5,
    "Sun": 6,
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
    "Tues": 1,
    "Thurs": 3,
    "Satur": 5,
}
WHITESPACE = re.compile(r"\s+")
FILENAME = re.compile(
    r"Route (\w) Schedules? \- ([A-Z][a-z]*)(\-([A-Z][a-z]*))?\.(csv|CSV)"
)
ONE_DAY = datetime.timedelta(days=1)
BLANK_ROW = itertools.repeat("")
header_replacements = {}

def any_multi(iterable, at_least=1):
    '''
    Returns True if the iterable has at least at_least elements that are true.
    '''
    for element in iterable:
        if element:
            at_least -= 1
            if at_least <= 0:
                return True
    return False
def one_equal_others_one_true(*iterables):
    '''
    Returns True if:
    - the values at exactly one position in all the given iterables are equal.
    - at all other positions, at most one value is truthy.
    '''
    equal = False
    for items in itertools.zip_longest(*iterables, fillvalue=False):
        if items[1:] == items[:-1]:
            # The values at this position in all the given iterables are equal.
            if equal:
                # Oops, this already happened at an earlier position. This
                # means that the values at more than one position are equal.
                return False
            equal = True
        else:
            truthy = False
            for item in items:
                if item:
                    # This value is truthy.
                    if truthy:
                        # Oops, the value at this position in one of the other
                        # iterables is already truthy.
                        return False
                    truthy = True
    return equal
def clean_header(header):
    # Split by any whitespace. Remove empty elements.
    parts = collections.deque(
        w for w in WHITESPACE.split(header.strip().rstrip("*")) if w
    )
    # Remove words like "Arrival" and "Departure."
    # We could use a double-ended queue for parts, but these words do not
    # appear often enough to justify the overhead of creating 
    if parts:
        if parts[-1] == "Arrival" or parts[-1] == "Departure":
            parts.pop()
        elif parts[0] == "Arrival" or parts[0] == "Arrive":
            parts.popleft()
            if parts and parts[0] == "at":
                parts.popleft()
        elif parts[0] == "Departure" or parts[0] == "Depart":
            parts.popleft()
            if parts and parts[0] == "from":
                parts.popleft()
    # Expand abbreviations.
    parts = [
        ABBREVIATION_EXPANSION.get(p.strip("()").rstrip("."), p) for p in parts
    ]
    # Remove directional words.
    parts = [p for p in parts if p.strip("()") not in DIRECTIONAL_WORDS]
    # Put spaces back in.
    result = " ".join(parts)
    # Do the string replacements.
    for find, replace in header_replacements.items():
        result = result.replace(find, replace)
    return result
def clean_header_row(row):
    return [clean_header(h) for h in row]
def find_column(row, needle):
    '''
    Finds the index of the first occurrence of the needle in the given row.
    If the needle is not found, then it is appended to the row, and the new
    index is returned.
    '''
    try:
        return row.index(needle)
    except ValueError:
        pass
    # That column is not in the header row. Just add it.
    result = len(row)
    row.append(needle)
    return result
def parse_schedule_row(header_row, row, show_parse_error=True):
    '''
    This function parses a single row of strings from the schedule table into
    datetime.timedelta objects. It is assumed that the length of header_row is
    at least the length of row.
    
    In the schedule table, the stop names are the headers.
    
    Arguments:
        header_row: an iterable representing the stop names
        row: an iterable representing the row of strings to parse
    Returns:
        A list where every item is either None or a datetime.timedelta object.
        None means that the bus does not stop at that stop.
    '''
    last_header = None
    last_delta = None
    result_row = []
    via_other_route = None
    for h, v in zip(header_row, row):
        result_cell = None
        # Normalize whitespace.
        v = WHITESPACE.sub(" ", v.strip())
        # Ignore blank cells and cells that only contain "-".
        if v and v != "-":
            # Check for strings that represent times but that are not times.
            if v == "Soft Stop":
                if last_delta is not None:
                    minutes = pickle_nyu_unwritten_times.get_minutes(
                        last_header,
                        h
                    )
                    if minutes is not None:
                        result_cell = NYUTime(
                            last_delta.time +
                            datetime.timedelta(minutes=minutes),
                            False,
                            True
                        )
                else:
                    print("A soft stop cannot be the first stop.")
            elif v.startswith("Continues to "):
                if last_delta is not None:
                    destination = clean_header(v[13:])
                    minutes = pickle_nyu_unwritten_times.get_minutes(
                        last_header,
                        destination
                    )
                    if minutes is not None:
                        result_cell = NYUTime(
                            last_delta.time +
                            datetime.timedelta(minutes=minutes),
                            True,
                            False
                        )
                        # Instead of appending this result at the current
                        # position, we must put it in a new column for the
                        # destination.
                        i = find_column(header_row, destination)
                        while i >= len(result_row):
                            result_row.append(None)
                        result_row[i] = result_cell
                        # The bus may not make any more stops.
                        break
                else:
                    print("A route deviation cannot be the first stop.")
            elif v.startswith("Via Route "):
                # This row is on this schedule but actually for a different
                # route. NYU is confusing sometimes.
                via_other_route = v[10:]
            else:
                try:
                    # We have checked for all know strings that represent times
                    # but that are not actually times. We will now parse the
                    # string as a time.
                    parsed = dateutil.parser.parse(v)
                except ValueError:
                    if show_parse_error:
                        print("Unknown time value:", repr(v))
                else:
                    # Get just the time.
                    parsed = parsed.time()
                    if parsed not in IGNORED_TIMES:
                        # Convert this to the timedelta after midnight.
                        parsed = datetime.datetime.combine(
                            datetime.datetime.min,
                            parsed
                        ) - datetime.datetime.min
                        # Make this timedelta is longer than the last.
                        if last_delta is not None:
                            while parsed <= last_delta.time:
                                parsed += ONE_DAY
                        # Convert this into an NYUTime object.
                        result_cell = NYUTime(parsed, True, False)
        # Save this cell.
        result_row.append(result_cell)
        if result_cell is not None:
            last_header = h
            last_delta = result_cell
    # Strip None values from the end of the list.
    while result_row and result_row[-1] is None:
        result_row.pop()
    return result_row, via_other_route
def read_google_sheet(workbook_key, sheet_gid):
    r = requests.get(
        "https://spreadsheets.google.com/feeds/download/spreadsheets/Export",
        params={"key": workbook_key, "gid": sheet_gid, "exportFormat": "csv"}
    )
    if r.ok:
        filename = None
        for part in r.headers["Content-Disposition"].split(";"):
            part = part.strip()
            if part.startswith("filename*=UTF-8''"):
                filename =  urllib.parse.unquote(part[17:])
        return io.StringIO(r.text), filename
    return None, None
def read_csv_io(csv_io):
    header_row = []
    other_rows = []
    other_routes = collections.defaultdict(list)
    if csv_io:
        # Tabula should return the data in CSV format. Let's read it.
        reader = iter(csv.reader(csv_io))
        # Sometimes, the headers are split among several rows.
        # Recombine them into one row.
        row = ()
        while True:
            # Read the next row.
            try:
                row = next(reader)
            except StopIteration:
                break
            # Skip rows that have only one non-empty cell.
            if any_multi(row, 2):
                # Parse this row for times.
                if parse_schedule_row(BLANK_ROW, row, show_parse_error=False)[0]:
                    # Times were found.
                    # This row will be processed again in the next while loop.
                    break
                # If no times were found, this row is a part of the headers.
                header_row = [
                    a + "\n" + b for a, b in itertools.zip_longest(
                        header_row,
                        row,
                        fillvalue=""
                    )
                ]
        # Clean up the headers.
        header_row = clean_header_row(header_row)
        # Parse the times.
        while True:
            # Process the last seen row.
            # Skip rows that have only one non-empty cell.
            if any_multi(row, 2):
                result_row, via_other_route = \
                    parse_schedule_row(header_row, row)
                if result_row:
                    if via_other_route:
                        other_routes[via_other_route].append(result_row)
                    else:
                        other_rows.append(result_row)
            # Get the next row.
            try:
                row = next(reader)
            except StopIteration:
                break
        # Remove columns with blank headings.
        to_pop = [i for i, header in enumerate(header_row) if not header]
        for i in reversed(to_pop):
            header_row.pop(i)
            for row in itertools.chain(
                # Loop through every row.
                other_rows,
                # Loop through rows that are for other routes, too.
                itertools.chain.from_iterable(
                    other_routes.values()
                )
            ):
                if i < len(row):
                    row.pop(i)
    return header_row, other_rows, other_routes
def main():
    # Read the table of schedules.
    schedules = []
    try:
        with open(SCHEDULES, "r", newline="", encoding="UTF-8") as f:
            for i, row in enumerate(csv.DictReader(f), start=1):
                try:
                    schedules.append({
                        "workbook_key": row["Key"],
                        "sheet_gid": row["GID"],
                        "filename_override": row["Filename Override"]
                    })
                except KeyError as e:
                    print(
                        "The table of schedules is missing this column:",
                        repr(e.args[0])
                    )
                    return
                except ValueError as e:
                    print("Error on line ", i, ": ", e, sep="")
    except OSError as e:
        print("Cannot open table of schedules:", e)
    # Read the table of string replacements for the header row.
    try:
        with open(REPLACEMENTS, "r", newline="", encoding="UTF-8") as f:
            for row in csv.DictReader(f):
                try:
                    header_replacements[row["Find"]] = row["Replace"]
                except KeyError as e:
                    print(
                        "The table of header string replacements is missing "
                        "this column:",
                        repr(e.args[0])
                    )
                    return
    except OSError as e:
        print("Cannot open table of header string replacements", e)
    # Save a list of nodes for finding walking times later.
    node_list = set()
    # Keep track of rows that need to be added to other routes.
    other_routes_all = []
    # Organize schedules by the day of the week.
    schedule_by_day = [[] for i in range(7)]
    # Parse the schedules.
    schedules_parsed = []
    with multiprocessing.pool.ThreadPool() as pool:
        # Process every schedule.
        print(
            "It is assumed that all schedules are sorted from earliest to "
            "latest."
        )
        def callback(schedule):
            print("Processing:", schedule)
            filename_override = schedule.pop("filename_override")
            csv_io, filename = read_google_sheet(**schedule)
            header_row, other_rows, other_routes = read_csv_io(csv_io)
            if filename_override:
                filename = filename_override
            return filename, header_row, other_rows, other_routes
        for filename, header_row, other_rows, other_routes in pool.imap(
            callback,
            schedules
        ):
            print("Completed: ", filename)
            # Get the route letter and days of the week from the filename.
            match = FILENAME.fullmatch(filename)
            if match is None:
                print("Bad filename format:", repr(filename))
            else:
                route, dow_start, _, dow_end, _ = match.groups()
                try:
                    if dow_end is None:
                        if dow_start == "Weekend" or dow_start == "Weekends":
                            days_of_week = (5, 6)
                        elif dow_start == "Weekday" or dow_start == "Weekdays":
                            days_of_week = range(0, 5)
                        else:
                            days_of_week = (DAYS_OF_WEEK_REVERSE[dow_start],)
                    else:
                        days_of_week = range(
                            DAYS_OF_WEEK_REVERSE[dow_start],
                            DAYS_OF_WEEK_REVERSE[dow_end] + 1
                        )
                except KeyError as e:
                    print("Unknown day of week:", repr(e.args[0]))
                else:
                    if days_of_week:
                        # Create the schedule object.
                        schedule = NYUSchedule(
                            route,
                            header_row,
                            other_rows,
                            days_of_week
                        )
                        schedules_parsed.append((filename, schedule))
                        # Assign it to the specified days of the week.
                        for dow in days_of_week:
                            schedule_by_day[dow].append(schedule)
                        # Store the rows that need to be added to other routes.
                        for route, rows in other_routes.items():
                            other_routes_all.append(
                                NYUSchedule(
                                    route,
                                    header_row,
                                    rows,
                                    days_of_week
                                )
                            )
            # Save any new nodes for the walking agency.
            node_list.update(header_row)
    # Add to other routes the rows that need to be added to other routes.
    migrations = []
    for schedule_source_index, schedule_source in enumerate(other_routes_all):
        # Find rows in the source schedule that can fit into a destination
        # schedule.
        for row_source_index, row_source in \
            enumerate(schedule_source.other_rows):
            found = False
            # Find the schedule to which the rows need to be added.
            for schedule_destination_index, schedule_destination in \
                enumerate(schedule_by_day[schedule_source.days_of_week[0]]):
                if schedule_source.route == schedule_destination.route:
                    # If the destination header row does not end with the
                    # source header row, concatenate the source header row onto
                    # the destination header row. Columns that contain no data,
                    # not counting the header row, will be deleted later.
                    if len(schedule_destination.header_row) < \
                        len(schedule_source.header_row) or \
                        schedule_destination.header_row \
                            [-len(schedule_source.header_row):] != \
                        schedule_source.header_row:
                        schedule_destination.header_row.extend(
                            schedule_source.header_row
                        )
                    # Find ways that the headings of the two schedules could be
                    # joined until a way that works is found.
                    for column_indices in \
                        schedule_destination.get_columns_indices(
                            *schedule_source.header_row
                        ):
                        # Look for a row in the destination schedule where:
                        # - the time for one stop matches both schedules.
                        # - the times for all other stops are in one schedule
                        #   schedule but not both.
                        for row_destination_index, row_destination in \
                            enumerate(schedule_destination.other_rows):
                            if one_equal_others_one_true(
                                row_source,
                                (
                                    (
                                        row_destination[index]
                                        if index < len(row_destination) else
                                        False
                                    )
                                    for index in column_indices
                                )
                            ):
                                # This row satisfies the conditions! We can
                                # copy the stop times from the source row to
                                # the destination row. We cannot modify data
                                # structures while looping through them, so
                                # just make a note of this operation for later.
                                migrations.append(
                                    (
                                        schedule_source_index,
                                        row_source_index,
                                        schedule_destination_index,
                                        row_destination_index,
                                        column_indices
                                    )
                                )
                                # Move on to the next source row.
                                found = True
                                break
                        if found:
                            break
                    if found:
                        break
    for schedule_source_index, row_source_index, \
        schedule_destination_index, row_destination_index, \
        column_indices in reversed(migrations):
        # Retrieve the schedules.
        schedule_source = other_routes_all[schedule_source_index]
        schedule_destination = \
            schedule_by_day \
                [schedule_source.days_of_week[0]][schedule_destination_index]
        # If the days of the week for both schedules are not the same, then
        # make a deep copy of the destination schedule. It will replace the old
        # destination schedule on days of the week where the schedule will not
        # be modified.
        sssdow = set(schedule_source.days_of_week)
        ssddow = set(schedule_destination.days_of_week)
        if sssdow != ssddow:
            schedule_destination_copy = copy.deepcopy(schedule_destination)
            for dow in sssdow - sssdow:
                schedule_by_day[dow].remove(schedule_destination)
                schedule_by_day[dow].append(schedule_destination_copy)
        # Execute the copying.
        row_source = schedule_source.other_rows[row_source_index]
        row_destination = \
            schedule_destination.other_rows[row_destination_index]
        for index_source, index_destination in enumerate(column_indices):
            while len(row_destination) <= index_destination:
                row_destination.append(None)
            row_destination[index_destination] = row_source[index_source]
        # Now that the source row has been copied, delete it.
        schedule_source.other_rows.pop(row_source_index)
    for schedule_source in other_routes_all:
        # If there are rows that were not copied, then accept the
        # source schedule as an extra schedule. Only include the rows
        # that were not copied.
        if schedule_source.other_rows:
            for dow in schedule_source.days_of_week:
                schedule_by_day[dow].append(schedule_source)
            schedules_parsed.append(("<Found>", schedule_source))
    # Delete columns that contain no data, not counting the header row.
    for schedule in itertools.chain.from_iterable(schedule_by_day):
        for index in reversed(
            range(
                max(
                    len(schedule.header_row),
                    max(len(row) for row in schedule.other_rows)
                )
            )
        ):
            empty = True
            for row in schedule.other_rows:
                if index < len(row) and row[index]:
                    empty = False
                    break
            if empty:
                schedule.header_row.pop(index)
                for row in schedule.other_rows:
                    if index < len(row):
                        row.pop(index)
    # Create an HTML file that humans can use to double-check our work.
    with open(NYU_HTML, "w", encoding="UTF-8") as f:
        f.write(
            '<!DOCTYPE HTML>\n<html>\n\t<head>\n\t\t<meta charset="UTF-8">\n'
            '\t\t<title>NYU Bus Schedules</title>\n\t<style type="text/css">\n'
            'h1{font-family:Segoe UI Semilight,sans-serif}'
            'p,table{font-family:Segoe UI,sans-serif}'
            'table{border-collapse:collapse}'
            'th,td{border:1px solid;padding:2pt 4pt;white-space:nowrap}'
            '\t\t</style>\n\t</head>\n\t<body>\n'
        )
        for filename, schedule in schedules_parsed:
            # Save our work for humans to check.
            f.write('\t\t<h1>')
            f.write(cgi.escape(filename))
            f.write('</h1>\n\t\t<p>Schedule for Route ')
            f.write(schedule.route)
            f.write(" (")
            f.write(
                ", ".join(
                    DAYS_OF_WEEK[dow] for dow in schedule.days_of_week
                )
            )
            f.write(')</p>\n\t\t<table>\n\t\t\t<tr>\n')
            for h in schedule.header_row:
                f.write('\t\t\t\t<th>')
                f.write(cgi.escape(str(h)))
                f.write('</th>\n')
            f.write('\t\t\t</tr>\n')
            for row in schedule.other_rows:
                f.write('\t\t\t<tr>\n')
                for c in row:
                    f.write('\t\t\t\t<td>')
                    if c is not None:
                        f.write(cgi.escape(str(c)))
                    f.write('</td>\n')
                for _ in range(len(schedule.header_row) - len(row)):
                    f.write('\t\t\t\t<td></td>\n')
                f.write('\t\t\t</tr>\n')
            f.write('\t\t</table>\n')
        # Finish it up for the humans.
        f.write('\t</body>\n</html>\n')
    # Output the pickled schedule.
    with open(NYU_PICKLE, "wb") as f:
        pickle.dump(schedule_by_day, f)
    # Remove the unnamed node if it is present.
    try:
        node_list.remove("")
    except KeyError:
        pass
    # Output the list for the walking agency.
    with open(NODE_LIST_TXT, "w", encoding="UTF-8") as f:
        for node in sorted(node_list):
            print(node, file=f)
    print("Done.")

if __name__ == "__main__":
    main()
