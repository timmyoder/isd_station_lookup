import pandas as pd
import numpy as np
import datetime as dt
import time

import peewee as pw
from playhouse.sqlite_udf import sqrt
from geopy import distance as geo_dist

from models import StationHistory
from config import INPUT_DIR


def select_closest_stations(lat_target, lon_target, active_only=True):
    """
    selects the 100 closest stations to the target location

     Distance calculated as the square of the euclidean distance
     between station locations and target location.

     distances = (d_LAT)^2 + (d_LON)^2

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
    """Actualates the actual distance (in miles) betwee the target lat/lon
    and the stations' location

    Uses geopy.geo_dist.distance. Two or three times slower than
    calc_distance_euclidean()
    """

    locations['distance_miles'] = locations.apply(
        lambda x: geo_dist.distance((x['LAT'], x['LON']),
                                    (lat_target, lon_target),
                                    ).miles,
        axis=1)

    return locations


def find_closest(lat_target,
                 lon_target,
                 active_only=True,
                 return_tuple=False):
    """finds the closest station as defined

    Performance of distance_type method
    actual: 0.019243001000000093 s
    euclid: 0.008490397999999955 s
    """
    close_stations = select_closest_stations(lat_target=lat_target,
                                             lon_target=lon_target,
                                             active_only=active_only)

    close_stations = calc_distance_actual(close_stations,
                                          lat_target,
                                          lon_target)

    # remove stations with USAF=999999
    close_stations = close_stations[close_stations['USAF'] != '999999']

    closest = close_stations.loc[close_stations.distance_miles ==
                                 close_stations['distance_miles'].min()]
    if not return_tuple:
        return closest
    return (closest['USAF'].values[0],
            closest['WBAN'].values[0],
            closest['distance_miles'].values[0])


def find_closest_csv(file_name, active_only=True, distance_type='actual'):
    input_file = INPUT_DIR / file_name
    if not input_file.is_file():
        raise ValueError(f'{file_name} not found in {INPUT_DIR}')

    points = pd.read_csv(input_file)

    if 'Latitude' not in points.columns or 'Longitude' not in points.columns:
        raise ValueError('Input file must have columns with the labels: "Latitude" and "Longitude"')

    stns = pd.DataFrame(points.apply(
        lambda x: find_closest(lat_target=x['Latitude'],
                               lon_target=x['Longitude'],
                               active_only=active_only,
                               return_tuple=True),
        axis=1).tolist(),
                        columns=['USAF', 'WBAN', 'distance_miles'],
                        index=points.index)

    labeled_points = pd.concat([points, stns], axis=1)

    return labeled_points


if __name__ == '__main__':
    rand = find_closest_csv('rand.csv', distance_type='actual')
    # t = select_closest_stations(47.651910, -122.343435)
    # t = find_closest(47.651910, -122.343435)
