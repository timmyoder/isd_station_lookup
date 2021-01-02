import pandas as pd
import numpy as np
import datetime as dt
import time

import peewee as pw
from geopy import distance as geo_dist

from models import StationHistory


def select_close_stations(lat_target, lon_target, active_only=True):
    """selects stations from the database within +/- 1 degree lat and lon."""
    query = StationHistory.select().where(
        StationHistory.LON.between(lon_target - 1, lon_target + 1) &
        StationHistory.LAT.between(lat_target - 1, lat_target + 1)
    )

    close_stations = pd.DataFrame(list(query.dicts()))

    if active_only:
        two_wks_ago = dt.date.today() - dt.timedelta(weeks=2)
        active_stns = close_stations[close_stations['END'] > two_wks_ago]
        return active_stns
    return close_stations


def calc_distance_euclidean(locations, lat_target, lon_target):
    locations['distance'] = np.sqrt(
        np.square(locations['LON'] - lon_target) +
        np.square(locations['LAT'] - lat_target)
    )
    return locations


def calc_distance_actual(locations, lat_target, lon_target):
    locations['distance'] = locations.apply(
        lambda x: geo_dist.distance((x['LAT'], x['LON']),
                                    (lat_target, lon_target),
                                    ).miles,
        axis=1)

    return locations


def find_closest(lat_target,
                 lon_target,
                 active_only=True,
                 distance_type='actual'):
    """finds the closest station as defined by euclidean distance"""
    close_stations = select_close_stations(lat_target=lat_target,
                                           lon_target=lon_target,
                                           active_only=active_only)

    if distance_type == 'actual':
        close_stations = calc_distance_actual(close_stations,
                                              lat_target,
                                              lon_target)
    elif distance_type == 'euclidean':
        calc_distance_euclidean(close_stations,
                                lat_target,
                                lon_target)
    else:
        raise ValueError('Distance type must be "actual" or "euclidean"')

    # remove stations with USAF=999999
    close_stations = close_stations[close_stations['USAF'] != '999999']

    closest = close_stations.loc[close_stations.distance ==
                                 close_stations['distance'].min()]
    return closest


if __name__ == '__main__':
    t0 = time.perf_counter()

    e = find_closest(47.651914, -122.343461, active_only=True, distance_type='actual')
    t1 = time.perf_counter()
    print(f'euclidean: {t1 - t0}')

    act = find_closest(47.651914, -122.343461, active_only=True, distance_type='euclidean')
    t2 = time.perf_counter()
    print(f'actual: {t2 - t1}')
