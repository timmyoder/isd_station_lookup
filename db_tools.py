import pandas as pd
import ftplib
from io import BytesIO
from peewee import IntegrityError, OperationalError
from loguru import logger

from config import RESOURCE_DIR
from models import StationHistory, clear_db


def download_history():
    """downloads the most recent station history file from the NOAA FTP site"""
    ftp_host = "ftp.ncdc.noaa.gov"

    with ftplib.FTP(host=ftp_host) as ftpconn:
        ftpconn.login()

        ftp_file = f"pub/data/noaa/isd-history.csv"
        # read the whole file and save it to a BytesIO (stream)
        response = BytesIO()
        try:
            ftpconn.retrbinary('RETR ' + ftp_file, response.write)

        except ftplib.error_perm as err:
            if str(err).startswith('550 '):
                print('ERROR:', err)
            else:
                raise FileNotFoundError

        # decompress and parse each line
        response.seek(0)  # jump back to the beginning of the stream
        content = response.read()

        history_file = RESOURCE_DIR / 'isd-history.csv'
        with open(history_file, 'wb') as outFile:
            outFile.write(content)
    logger.info('New ISD history file downloaded')


def populate_db():
    history_file = RESOURCE_DIR / 'isd-history.csv'
    history = pd.read_csv(history_file,
                          dtype={'USAF': str,
                                 'WBAN': str},
                          parse_dates=['BEGIN', 'END'])
    history.columns = ['USAF', 'WBAN', 'STATION_NAME', 'CTRY', 'STATE',
                       'ICAO', 'LAT', 'LON', 'ELEV', 'BEGIN', 'END']

    station_list = history.to_dict('records')

    # SQLITE_MAX_VARIABLE_NUMBER default 50000 (MacOS). limit bulk inserts to chunks

    CHUNK_SIZE = 10000

    current_index = 0

    try:
        while current_index < len(station_list) - 1:
            end_index = current_index + CHUNK_SIZE
            if end_index > len(station_list) - 1:
                station_chunk = station_list[current_index:]
            else:
                station_chunk = station_list[current_index:end_index]
            count = StationHistory.insert_many(station_chunk).execute()
            logger.info(f'{count} stations added to db')
            current_index += CHUNK_SIZE
    except OperationalError as error:
        logger.error(error)
        logger.error('CHUNK_SIZE exceeds SQLITE_MAX_VARIABLE_NUMBER on your machine')
    except IntegrityError as error:
        logger.error(error)
        logger.error('Records not inserted')
    logger.success('All stations added')


def refresh_db():
    download_history()
    clear_db()
    populate_db()


if __name__ == '__main__':
    refresh_db()
