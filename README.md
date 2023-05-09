# UltRank Scoring Bundle

Allows for quick scoring of events for UltRank.

## Requirements

- Python
- Necessary packages: run `pip install -r ultrank_requirements.txt` to install all necessary packages.
  - geopy
  - dateparser
  - levenshtein
- startgg API key stored in a `smashgg.key` file in the same directory
- versions of the three CSVs included.

## ultrank_tiering.py

Tiers a single event with a rudimentary user interface. Also contains logic for tiering events.

## ultrank_bulk.py

Tiers multiple events in succession based on an input file. Writes the results to files on your machine.

### Requirements

- all requirements for `ultrank_tiering.py`
- file containing a list of tournament keys to evaluate
  - If this file is a CSV, it requires the columns to be named.
    - start.gg slugs should be headered under `startgg slug`
    - truthy invitational values should be headered under `Is Invitational?`
  - You will be asked to input the path to this file in the user interface
 
### Notes
 
- All results will be stored in the `tts_values` directory relative to where you initiated the script.
- An overview will be stored in the `summary.csv` file.
- Each event will have its own `txt` file with its point breakdown.
- Blank lines or invalid keys in the original input file will be accounted for in the `summary.csv` file.
- The `Meets Reqs` column indicates whether or not a tournament meets attendance / qualification requirements to actually be counted in UltRank.

## ultrank_search.py

Searches start.gg to find all tournaments within a given range, and checks them to see if they qualify.  
Note that this process may take a long time for longer time ranges.

### Notes

- You will be asked to input the start and end time for searching. I recommend increasing your search range a little bit from what you want, just in case.
- This script uses a rudimentary string-similarity algorithm to detect potential weeklies. It is not 100% accurate.
- An overview of all events checked will be stored in the `events.csv` file, which is contained in the `tts_values` directory mentioned above. This file contains all events looked at, and for events that were skipped, provides a quick justification. Use this file to determine if any tournaments were overlooked.
