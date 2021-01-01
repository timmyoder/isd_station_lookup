import os

import peewee as pw
from loguru import logger

from config import RESOURCE_DIR

db_file = RESOURCE_DIR / 'isd_history.db'

db = pw.SqliteDatabase(db_file)


class BaseModel(pw.Model):
    class Meta:
        """required for each class"""
        database = db


class StationHistory(BaseModel):
    USAF = pw.CharField()
    WBAN = pw.CharField()
    STATION_NAME = pw.CharField(null=True)
    CTRY = pw.CharField(null=True)
    STATE = pw.CharField(null=True)
    ICAO = pw.CharField(null=True)
    LAT = pw.FloatField(null=True)
    LON = pw.FloatField(null=True)
    ELEV = pw.FloatField(null=True)
    BEGIN = pw.DateField(null=True)
    END = pw.DateField(null=True)

    class Meta:
        indexes = (
            (("USAF", "WBAN"), True),
        )


def clear_db():
    if db_file.exists():
        os.remove(db_file)
        logger.info('existing database deleted')
    db.connect()
    db.create_tables([StationHistory])
    logger.info('New db file create')


if __name__ == '__main__':
    clear_db()
