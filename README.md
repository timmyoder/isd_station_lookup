# NOAA ISD Weather Station Lookup
Look up the closest [NOAA ISD](https://www.ncdc.noaa.gov/isd) weather station from an latitude/longitude input. A single point can be provided, or list of points in an input CSV file with 'Latitude', 'Longitude' columns.

## Project Structure

* `db_tools.py` contains tools to download the most recent station history file from the NOAA FTP site.
* `models.py` defines and creates a SQLite db to store all station information. db is stored at `resources/isd_history.db`
* `config.py` creates the required directories and handles the file path management.
* `lookup.py` finds the closest station to either a single lat/lon point or a list of stations defined in an input csv file.
	* The closest 100 points to the target location are pulled from the database. The stations that are no longer active are filtered out, as well as stations with a USAF of '999999'. 
	* The actual distance [in miles] are calculated for each of those stations and then the station with the smallest distance is returned for the target station.

## Setup

If you have the conda package manager install, running the following command inside the repository directory to create a new conda env (named `stns_env`).

```
conda env create -f environment.yml
```

To download the current csv history file and create/populate the SQLite database run: 

```
python db_tools.py
```

The `input_data/`, `output_data/`, and `resources/` directories are all automatically created at this point.

## Get Station Information

Place a csv file with target lat/lon points into the `input_data/` directory. **The csv file must contain columns named 'Latitude' and 'Longitude' with their respecitve points in decimal form (i.e. 47.651, -122.343).** Columns with the stations USAF id, WBAN id, and the distance [in miles] between the target location and station are added to the csv file and saved in the `output_data/` directory. You must have run the commands list in the Setup section for it to work.
