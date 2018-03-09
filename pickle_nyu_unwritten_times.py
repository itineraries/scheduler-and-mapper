#!/usr/bin/env python3
'''
This module is responsible for telling pickle_nyu how long it takes the bus to
get from one place to another. Normally, the schedule has this information.
However, for some reason, NYU decided not to include the information for some
stops. That's why it has to be provided by this module.

The information is stored in "Driving Time Overrides.csv". When this module
does not know the driving time from one stop to another, those two stops are
written to this file with a question mark for the time. It is up to you to put
the correct time in.
'''
import atexit, csv, multiprocessing, os.path, sys
from common import file_in_this_dir
UNWRITTEN_TIMES_CSV = file_in_this_dir("Driving Time Overrides.csv")
linit = multiprocessing.Lock()
unwritten_times = None

def save():
    '''
    This function saves the driving times back to UNWRITTEN_TIMES_CSV. There is
    no need to call this function from outside the module; it is automatically
    called when the module is exited.
    
    This function is not thread-safe.
    '''
    global unwritten_times
    if unwritten_times is not None:
        unwritten_times.pop(("", ""), 0)
        with open(UNWRITTEN_TIMES_CSV, "w", newline="", encoding="UTF-8") as f:
            writer = csv.writer(f)
            writer.writerow(("From", "To", "Minutes"))
            for (f, t), minutes in unwritten_times.items():
                writer.writerow((f, t, minutes))
def read():
    '''
    This function reads the driving times from UNWRITTEN_TIMES_CSV and
    populates this module's internal data. There is no return value. There is
    no need to call this function from outside the module because get_minutes
    calls this function automatically if it has not been called already.
    
    This function is not thread-safe.
    '''
    global unwritten_times
    unwritten_times = {("", ""): 0}
    try:
        with open(UNWRITTEN_TIMES_CSV, "r", newline="", encoding="UTF-8") as f:
            for line in csv.DictReader(f):
                try:
                    minutes = int(line["Minutes"])
                except ValueError:
                    pass
                else:
                    unwritten_times[(line["From"], line["To"])] = minutes
    except FileNotFoundError:
        pass
    except KeyError as e:
        print(
            "The", repr(e.args[0]), "column is missing the driving times.",
            "Fix it here:", repr(UNWRITTEN_TIMES_CSV)
        )
        return
    atexit.register(save)
def get_minutes(last_header, curr_header):
    global unwritten_times
    # If the driving times have not been loaded, load them.
    with linit:
        if unwritten_times is None:
            read()
    # Get the time from the dictionary.
    try:
        minutes = unwritten_times[(last_header, curr_header)]
    except KeyError:
        print(
            "We need the driving time from ", repr(last_header),
            " to ", repr(curr_header), ". Please edit ",
            repr(UNWRITTEN_TIMES_CSV),
            " to include this information.",
            sep="",
            file=sys.stderr
        )
        unwritten_times[(last_header, curr_header)] = "?"
    else:
        if minutes != "?":
            return minutes
    return None
