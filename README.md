# NOAA ISD Weather Station Lookup
Look up the closest [NOAA ISD](https://www.ncdc.noaa.gov/isd) weather station to target latitude/longitude location(s). A single point can be provided, or list of points in an input CSV file with 'Latitude', 'Longitude' columns.

## Project Structure

* `db_tools.py` contains tools to download the most recent station history file from the NOAA FTP site.
* `models.py` defines and creates a SQLite db to store all station information. db is stored at `resources/isd_history.db`
* `config.py` creates the required directories and handles the file path management.
* `lookup.py` finds the closest station to either a single lat/lon point or a list of stations defined in an input csv file.
	* The closest 100 points to the target location are pulled from the database. 
	* Stations that meet one or more of the following criteria are droped:
		* 'END' date not within the last two weeks. 
		* USAF of '999999' 
		* USAF that starts with 'A'. EX: 'A00023'. 
		* WBAN of '99999'.
	* The actual distance [in miles] is calculated for each of those stations and then the station with the smallest distance is returned for the target station.

## Setup

If you have the [conda package manager](https://docs.anaconda.com/anaconda/install/) installed, running the following commands inside the repository directory will create and activate a new conda env (named `stns_env`):

```
conda env create -f environment.yml
conda activate stns_env
```

To download the current csv history file and create/populate the SQLite database run: 

```
python db_tools.py
```

The `input_data/`, `output_data/`, and `resources/` directories are all automatically created at this point.

## Get Station Information

The program can be run from the command line. You must have completed the steps in [Setup](#Setup). 

usage

* `python lookup.py [-h] [--point POINT POINT] [--file FILE] [--include_inactive]`

### Finding the closest station to a point

usage

*  `python lookup.py --point LATITUDE LONGITUDE`

example

* `python lookup.py --point 47.651 -122.343`

Which prints the following table to the console:

| USAF   | WBAN  | STATION_NAME               | LAT   | LON      | BEGIN      | END        | CTRY | STATE | ELEV | ICAO | distance_miles |
|--------|-------|----------------------------|-------|----------|------------|------------|------|-------|------|------|----------------|
| 727935 | 24234 | BOEING FLD/KING CO INTL AP | 47.53 | -122.301 | 1943-10-01 | 2020-12-29 | US   | WA    | 5.5  | KBFI | 8.587          |

### Finding the closest stations to a list of points

Place a csv file with target lat/lon points into the `input_data/` directory. **The csv file must contain columns named 'Latitude' and 'Longitude' with their respecitve points in decimal form (i.e. 47.651, -122.343).** Columns with the stations USAF id, WBAN id, and the distance [in miles] between the target location and station are added to the csv file and saved in the `output_data/` directory. 

usage

* `python lookup.py --file FILE_NAME`

example

* `python lookup.py --file my_input_file.csv`
* Which saves a file `[output_data/labeled_points.csv]` with the closest stations


