# UltRank Scoring Bundle

Allows for quick scoring of events for UltRank.

## ultrank_tiering.py

Tiers a single event with a rudimentary user interface. Also contains logic for tiering events.

### Requirements

- Python
- geopy - you can download it via `pip install geopy`
- startgg API key stored in a `smashgg.key` file in the same directory
- versions of the three CSVs included.

## ultrank_bulk.py

Tiers multiple events in succession based on an input file. Writes the results to files on your machine.

### Requirements

- all requirements for `ultrank_tiering.py`
- file containing a list of tournament keys to evaluate
 - If this file is a CSV, it supports a second column to denote invitationals with a truthy value.
 - You will be asked to input the path to this file in the user interface
 
### Notes
 
- All results will be stored in the `tts_values` directory relative to where you initiated the script.
- An overview will be stored in the `summary.csv` file.
- Each event will have its own `txt` file with its point breakdown.
- Blank lines or invalid keys in the original input file will be accounted for in the `summary.csv` file.
