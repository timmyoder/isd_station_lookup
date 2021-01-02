import datetime as dt
import pandas as pd
import numpy as np

from geopy import distance as geo_dist

from models import StationHistory
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

    # remove stations with USAF=999999
    close_stations = close_stations[close_stations['USAF'] != '999999']

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
    output_file = OUTPUT_DIR / 'labeled_stations.csv'
    labeled_points.to_csv(output_file, index=False)
    return labeled_points


if __name__ == '__main__':
    rand = find_closest_csv('rand.csv')
    # t = select_closest_stations(47.651910, -122.343435)
    # t = find_closest(47.651910, -122.343435)
