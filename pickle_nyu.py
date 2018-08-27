#!/usr/bin/env python3
# QA checklist:
# - No times in titles
# - No missing letters in titles
# - Blank cells in PDFs are still blank in the output
# - No words like "Arrival," "Arrive," "Depart," or "Departure" in titles
# - Randomly select some schedules, compare output to original PDF
import cgi, collections, csv, datetime, dateutil.parser, io, itertools, \
    multiprocessing.pool, os, pickle, re, subprocess, sys
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
    "Ave": "Avenue",
    "St": "Street",
    "street": "Street",
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
FILENAME = re.compile(r"Route (\w) ([A-Z][a-z]*)(\-([A-Z][a-z]*))?\.(pdf|PDF)")
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
    # Remove directional words.
    parts = [p for p in parts if p.strip("()") not in DIRECTIONAL_WORDS]
    # Expand abbreviations.
    parts = [ABBREVIATION_EXPANSION.get(p.rstrip("."), p) for p in parts]
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
    for h, v in zip(header_row, row):
        v = WHITESPACE.sub(" ", v.strip())
        result_cell = None
        if v:
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
        result_row.append(result_cell)
        if result_cell is not None:
            last_header = h
            last_delta = result_cell
    # Strip None values from the end of the list.
    while result_row and result_row[-1] is None:
        result_row.pop()
    return result_row
def read_pdf_table(filename, pages, area, column_boundaries):
    try:
        # Launch Tabula and parse out the table in the PDF document.
        argv = [
            "java",
            "-Dsun.java2d.cmm=sun.java2d.cmm.kcms.KcmsServiceProvider",
            "-jar", "tabula-1.0.2-jar-with-dependencies.jar",
            "--pages", pages, "--area", area
        ]
        if column_boundaries != "auto":
            if column_boundaries == "stream":
                argv.append("--stream")
            elif column_boundaries == "lattice":
                argv.append("--lattice")
            else:
                argv.append("--columns")
                argv.append(column_boundaries)
        argv.append(os.path.join(os.curdir, "NYU", filename))
        output = subprocess.check_output(argv)
    except FileNotFoundError:
        print("It looks like you do not have Java installed.")
    except subprocess.CalledProcessError as e:
        print("If the JAR file for Tabula is missing, download it here:")
        print("https://github.com/tabulapdf/tabula-java/releases/tag/v1.0.2")
        print("Otherwise, make sure that", repr(filename), "exists.")
    else:
        # Tabula should return the data in CSV format. Let's read it.
        reader = iter(csv.reader(io.StringIO(output.decode("UTF-8"))))
        # Sometimes, the headers are split among several rows.
        # Recombine them into one row.
        header_row = ()
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
                if parse_schedule_row(BLANK_ROW, row, show_parse_error=False):
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
        other_rows = []
        while True:
            # Process the last seen row.
            # Skip rows that have only one non-empty cell.
            if any_multi(row, 2):
                result_row = parse_schedule_row(header_row, row)
                if result_row:
                    other_rows.append(result_row)
            # Get the next row.
            try:
                row = next(reader)
            except StopIteration:
                break
        # Return the result.
        return header_row, other_rows
    return [], []
def main():
    # Read the table of schedules.
    schedules = []
    try:
        with open(SCHEDULES, "r", newline="", encoding="UTF-8") as f:
            for i, row in enumerate(csv.DictReader(f), start=1):
                try:
                    schedules.append({
                        "filename": row["Filename"],
                        "pages": row["Page"],
                        "area": row["Area (Top, Left, Bottom, Right)"],
                        "column_boundaries": row["Column Boundaries"]
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
    # Parse the schedules.
    with multiprocessing.pool.ThreadPool() as pool, \
        open(NYU_PICKLE, "wb") as out_nyu, \
        open(NYU_HTML, "w", encoding="UTF-8") as out_human, \
        open(NODE_LIST_TXT, "w", encoding="UTF-8") as out_walking:
        # Organize schedules by the day of the week.
        schedule_by_day = [[] for i in range(7)]
        # Create an HTML file that humans can use to double-check our work.
        out_human.write(
            '<!DOCTYPE HTML>\n<html>\n\t<head>\n\t\t<meta charset="UTF-8">\n'
            '\t\t<title>NYU Bus Schedules</title>\n\t<style type="text/css">\n'
            'h1{font-family:Segoe UI Semilight,sans-serif}'
            'p,table{font-family:Segoe UI,sans-serif}'
            'table{border-collapse:collapse}'
            'th,td{border:1px solid;padding:2pt 4pt;white-space:nowrap}'
            '\t\t</style>\n\t</head>\n\t<body>\n'
        )
        # Save a list of nodes for finding walking times later.
        node_list = set()
        # Process every schedule.
        print(
            "It is assumed that all schedules are sorted from earliest to "
            "latest."
        )
        def callback(schedule):
            print("Processing:", schedule["filename"])
            header_row, other_rows = read_pdf_table(**schedule)
            return schedule["filename"], header_row, other_rows
        for filename, header_row, other_rows in pool.imap(callback, schedules):
            print("Completed: ", filename)
            # Get the route letter and days of the week from the filename.
            match = FILENAME.fullmatch(filename)
            if match is None:
                print("Bad filename format:", repr(filename))
            else:
                route, dow_start, _, dow_end, _ = match.groups()
                try:
                    if dow_end is None:
                        days_of_week = (DAYS_OF_WEEK_REVERSE[dow_start],)
                    else:
                        days_of_week = range(
                            DAYS_OF_WEEK_REVERSE[dow_start],
                            DAYS_OF_WEEK_REVERSE[dow_end] + 1
                        )
                except KeyError as e:
                    print("Unknown day of week:", repr(e.args[0]))
                else:
                    for dow in days_of_week:
                        schedule_by_day[dow].append(
                            NYUSchedule(route, header_row, other_rows)
                        )
                    # Save our work for humans to check.
                    out_human.write('\t\t<h1>')
                    out_human.write(cgi.escape(filename))
                    out_human.write('</h1>\n\t\t<p>Schedule for Route ')
                    out_human.write(route)
                    out_human.write(" (")
                    out_human.write(
                        ", ".join(
                            DAYS_OF_WEEK[dow] for dow in days_of_week
                        )
                    )
                    out_human.write(')</p>\n\t\t<table>\n\t\t\t<tr>\n')
                    for h in header_row:
                        out_human.write('\t\t\t\t<th>')
                        out_human.write(cgi.escape(str(h)))
                        out_human.write('</th>\n')
                    out_human.write('\t\t\t</tr>\n')
                    for row in other_rows:
                        out_human.write('\t\t\t<tr>\n')
                        for c in row:
                            out_human.write('\t\t\t\t<td>')
                            if c is not None:
                                out_human.write(cgi.escape(str(c)))
                            out_human.write('</td>\n')
                        for _ in range(len(header_row) - len(row)):
                            out_human.write('\t\t\t\t<td></td>\n')
                        out_human.write('\t\t\t</tr>\n')
                    out_human.write('\t\t</table>\n')
            # Save any new nodes for the walking agency.
            node_list.update(header_row)
        pickle.dump(schedule_by_day, out_nyu)
        # Finish it up for the humans.
        out_human.write('\t</body>\n</html>\n')
        # Output the list for the walking agency.
        for node in sorted(node_list):
            print(node, file=out_walking)
    print("Done.")

if __name__ == "__main__":
    main()
