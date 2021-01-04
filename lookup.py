import datetime as dt
import pandas as pd
import numpy as np
import argparse
import warnings

from geopy import distance as geo_dist
from loguru import logger

from models import StationHistory, db_file
from db_tools import refresh_db
from config import INPUT_DIR, OUTPUT_DIR


def select_closest_stations(lat_target, lon_target, active_only=True):
    """
    selects the 100 closest stations to the target location

     Distance calculated as the square of the euclidean distance
     between station locations and target location.

     distances = (d_LAT)^2 + (d_LON)^2

     returns a dataframe with station information for each of the close stations

     """
    query = StationHistory.select(
        StationHistory.USAF,
        StationHistory.WBAN,
        StationHistory.STATION_NAME,
        StationHistory.LAT,
        StationHistory.LON,
        StationHistory.BEGIN,
        StationHistory.END,
        StationHistory.CTRY,
        StationHistory.STATE,
        StationHistory.ELEV,
        StationHistory.ICAO,
        ((StationHistory.LON - lon_target) * (StationHistory.LON - lon_target) +
         (StationHistory.LAT - lat_target) * (StationHistory.LAT - lat_target)
         )
    ).order_by(
        ((StationHistory.LON - lon_target) * (StationHistory.LON - lon_target) +
         (StationHistory.LAT - lat_target) * (StationHistory.LAT - lat_target))
    ).where(
        ~StationHistory.LON.is_null()
    ).limit(100)
    close_stations = pd.DataFrame(list(query.dicts()))
    close_stations.columns = ['USAF', 'WBAN', 'STATION_NAME', 'LAT',
                              'LON', 'BEGIN', 'END', 'CTRY',
                              'STATE', 'ELEV', 'ICAO', 'dist']

    if active_only:
        two_wks_ago = dt.date.today() - dt.timedelta(weeks=2)
        active_stns = close_stations[close_stations['END'] > two_wks_ago]
        return active_stns.reset_index(drop=True).drop(columns=['dist'])
    return close_stations.drop(columns=['dist'])


def calc_distance_actual(locations, lat_target, lon_target):
    """Calculates the actual distance (in miles) between the target lat/lon
    and the stations' location
    """

    locations['distance_miles'] = locations.apply(
        lambda x: np.round(geo_dist.distance((x['LAT'], x['LON']),
                                             (lat_target, lon_target),
                                             ).miles, 3),
        axis=1)

    return locations


def find_closest(lat_target,
                 lon_target,
                 active_only=True,
                 return_tuple=False):
    """finds the closest station to the target station"""
    close_stations = select_closest_stations(lat_target=lat_target,
                                             lon_target=lon_target,
                                             active_only=active_only)

    close_stations = calc_distance_actual(close_stations,
                                          lat_target,
                                          lon_target)

    # remove stations with USAF=999999 and WBAN=99999
    close_stations = close_stations[close_stations['USAF'] != '999999']
    close_stations = close_stations[close_stations['WBAN'] != '99999']

    # remove stations that have a USAF that starts with 'A'. EX: 'A00023'
    close_stations = close_stations[~close_stations['USAF'].str.startswith('A')]

    closest = close_stations.loc[close_stations.distance_miles ==
                                 close_stations['distance_miles'].min()]
    if not return_tuple:
        return closest
    return (closest['USAF'].values[0],
            closest['WBAN'].values[0],
            closest['distance_miles'].values[0])


def find_closest_csv(file_name, active_only=True):
    """finds the closest station for stations in an input csv.
    The csv file must contain two columns named 'Latitude' and 'Longitude'

    Columns with the stations USAF id, WBAN id, and the distance [in miles]
    between the target location and station are added to the csv file.
    """
    input_file = INPUT_DIR / file_name
    if not input_file.is_file():
        raise ValueError(f'{file_name} not found in {INPUT_DIR}')

    points = pd.read_csv(input_file)

    if 'Latitude' not in points.columns or 'Longitude' not in points.columns:
        logger.error("Input file doesn't contain 'Latitude' and 'Longitude' columns")
        raise ValueError('Input file must have columns with the labels: "Latitude" and "Longitude"')

    logger.info('Calculating locations...')

    stns = pd.DataFrame(points.apply(
        lambda x: find_closest(lat_target=x['Latitude'],
                               lon_target=x['Longitude'],
                               active_only=active_only,
                               return_tuple=True),
        axis=1).tolist(),
                        columns=['USAF', 'WBAN', 'distance_miles'],
                        index=points.index)

    labeled_points = pd.concat([points, stns], axis=1)
    output_file = OUTPUT_DIR / 'labeled_stations.csv'
    logger.info(f'Output file saved: {output_file}')
    labeled_points.to_csv(output_file, index=False)
    return labeled_points


def check_db_age():
    two_wks_ago = dt.date.today() - dt.timedelta(weeks=2)
    latest_date = StationHistory.select(
        StationHistory.END
    ).order_by(StationHistory.END.desc()).limit(1).scalar()

    if latest_date < two_wks_ago:
        while True:
            choice = input('Station database is out of date. \n'
                           'Proceed with download updated history file? [y/n]')
            if choice in ['y', 'yes', 'Y', 'YES']:
                refresh_db()
                break
            elif choice in ['n', 'no', "N", 'NO']:
                logger.error('Up-to-date Weather station database required')
                raise ValueError('Weather station database out of date')


def check_db_exists():
    if not db_file.exists():
        while True:
            choice = input('Station database does not exist. \n'
                           'Proceed with download history file? [y/n]')
            if choice in ['y', 'yes', 'Y', 'YES']:
                refresh_db()
                break
            elif choice in ['n', 'no', "N", 'NO']:
                logger.error('Weather station database required')
                raise FileNotFoundError('Weather station database required')


def main():

    # Create argument parser
    parser = argparse.ArgumentParser(
        description='Find closest NOAA weather station to target location(s)')
    parser.add_argument("--point", nargs=2, type=float,
                        help="specify target point's latitude and longitude. "
                             "Example: python lookup.py --point 47.65 -122.34")
    parser.add_argument("--file", type=str,
                        help="Name of input file with target points. "
                             "File must be in the 'input_data/' dir. "
                             "Do not include the path to the directory in the name. "
                             "Example: python lookup.py --file input.csv")
    parser.add_argument('--include_inactive', action="store_true",
                        help='include inactive stations in results')
    args = parser.parse_args()

    check_db_exists()

    check_db_age()

    active_only = not args.include_inactive

    if args.point is None and args.file is None:
        raise parser.error('A target point or input file of points must be given')

    if args.point is not None:
        lat = args.point[0]
        lon = args.point[1]
        if not -90 <= lat <= 90:
            logger.error('Latitude must between -90 and 90')
            raise ValueError('Latitude must between -90 and 90')

        if not -180 <= lon <= 180:
            logger.error('Longitude must between -180 and 180')
            raise ValueError('Longitude must between -180 and 180')

        closest = find_closest(lat_target=lat,
                               lon_target=lon,
                               active_only=active_only)
        logger.info(f'Closest station to {lat}, {lon} is:')
        print(closest)
        print('\n')
    if args.file is not None:
        find_closest_csv(file_name=args.file,
                         active_only=active_only)


if __name__ == '__main__':
    # rand = pd.DataFrame(data={'Latitude': np.random.default_rng().uniform(30, 45, 50),
    #                           'Longitude': np.random.default_rng().uniform(-70, -120, 50)})
    # rand.to_csv(INPUT_DIR / 'rand.csv')

    main()
