#!/usr/bin/env python3
import csv, json, sys
from common import NODE_LIST_TXT, file_in_this_dir
from common_walking import Point, STOP_LOCATIONS_CSV
sys.path.insert(0, file_in_this_dir("../string-match"))
import matcher
STOP_LOCATION_OVERRIDES = file_in_this_dir("Stop Location Overrides.csv")
STOPS_JSON = file_in_this_dir("NYU_Stops.json")

def main():
    with open(STOP_LOCATION_OVERRIDES, "a+") as fslo:
    # Build a dictionary of stops whose locations were manually specified.
        print("Reading stop location overrides...")
        fslo.seek(0)
        overrides = {}
        for row in csv.DictReader(fslo):
            if row["Latitude"] and row["Longitude"]:
                overrides[row["From PDFs"]] = Point(
                    row["Latitude"],
                    row["Longitude"]
                )
        # Prepare to rewrite them back into the file.
        fslo.seek(0)
        fslo.truncate()
        slowriter = csv.writer(fslo)
        slowriter.writerow((
            "From PDFs",
            "From API",
            "Latitude Guess",
            "Longitude Guess",
            "Latitude",
            "Longitude"
        ))
        # Build a list of stops whose locations were not manually specified.
        print("Reading node list from PDFs...")
        with open(NODE_LIST_TXT, "r") as f:
            nodes = [l.strip() for l in f]
        # Read all locations from the JSON file.
        print("Reading stops JSON from API...")
        with open(STOPS_JSON, "r") as f:
            api_stops = {}
            for d in json.load(f)["data"]:
                if d["location_type"] == "stop":
                    api_stops[d["name"]] = d["location"]
                    api_stops[
                        d["name"]
                            .replace("@", "At", 1)
                            .replace("St.", "Street")
                    ] = d["location"]
        # Run the string matcher on stop names from the two lists.
        print("Matching stop names...")
        matches = matcher.match_list_of_str(nodes, api_stops.keys())
        # Create a CSV file, which can be reviewed by the user.
        print("Writing stop locations...")
        with open(STOP_LOCATIONS_CSV, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ("From PDFs", "From API", "Score", "Latitude", "Longitude")
            )
            for match in matches:
                if match.from_list_a in overrides:
                    writer.writerow((
                        match.from_list_a,
                        "",
                        0,
                        overrides[match.from_list_a].lat,
                        overrides[match.from_list_a].lng
                    ))
                    slowriter.writerow((
                        match.from_list_a,
                        match.from_list_b,
                        api_stops[match.from_list_b]["lat"],
                        api_stops[match.from_list_b]["lng"],
                        overrides[match.from_list_a].lat,
                        overrides[match.from_list_a].lng
                    ))
                else:
                    if match.score > 1:
                        # This was not an exact match, so put it in the
                        # overrides file.
                        print(
                            " > Please check this stop in the overrides file:",
                            repr(match.from_list_a)
                        )
                        slowriter.writerow((
                            match.from_list_a,
                            match.from_list_b,
                            api_stops[match.from_list_b]["lat"],
                            api_stops[match.from_list_b]["lng"],
                            "",
                            ""
                        ))
                    writer.writerow((
                        match.from_list_a,
                        match.from_list_b,
                        match.score,
                        api_stops[match.from_list_b]["lat"],
                        api_stops[match.from_list_b]["lng"]
                    ))
    print("Done.")

if __name__ == "__main__":
    main()
