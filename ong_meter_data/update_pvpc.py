#!/usr/bin/python
import datetime
import time
import multiprocessing

from ong_utils import LOCAL_TZ
from ong_esios.esios_api import EsiosApi
import pandas as pd
from ong_meter_data import config, logger
from ong_tsdb.client import OngTsdbClient

_esios_bucket = config("esios_bucket")
_esios_sensor = "PVPC"
ongtsdb_client = OngTsdbClient(url=config('url'), token=config('admin_token'))
ongtsdb_client.create_db(_esios_bucket)
ongtsdb_client.create_sensor(_esios_bucket, _esios_sensor, "1h", metrics=list(),
                             read_key=config('read_token'), write_key=config('write_token'))


def update_esios(date):
    """Downloads pvpc from esios for the given date and writes into client"""
    start_t = time.time()
    esios = EsiosApi()
    # res = esios.download_by(name="pvpcdesglosehorario", date=date)
    res = esios.download("archives", 80, date=date)
    logger.info(f"Read esios data for day {date} in {time.time() - start_t:.3f}s")
    if res is None:
        logger.error(f"Error reading esios data for date {date}")
    else:
        pvpc_dates, pvpc_values = res['dates'], res['values']
        sequence = []
        for h, date in enumerate(pvpc_dates):
            timestamp_ns = date.value
            values = list('{k}={v:.2f}'.format(k=key, v=value[h]) for key, value in pvpc_values.items())
            if values:
                point = "{measurement},serie={sensor} {values} {timestamp}". \
                    format(measurement=config('esios_bucket'), sensor=_esios_sensor,
                           values=",".join(values), timestamp=timestamp_ns)
                sequence.append(point)
        if sequence:
            start_t = time.time()
            success = ongtsdb_client.write(sequence)
            logger.info(f"Written data for date {date}: {success} in {time.time() - start_t:.3f}s")
        else:
            logger.info(f"Nothing read in date {date}")


def main():
    """
    Reads data from esios for indicator named "pvpcdesglosehorario" (PVPC) and stores it in esios bucket,
    starting download from the last available date in database
    :return:
    """
    last_ts = ongtsdb_client.get_lasttimestamp(_esios_bucket, _esios_sensor)
    if last_ts:
        start_t = pd.Timestamp.utcfromtimestamp(last_ts).tz_convert("UTC").astimezone(LOCAL_TZ)
    else:
        start_t = pd.Timestamp(year=2014, month=4, day=1, tz=LOCAL_TZ)
    end_t = pd.Timestamp.today(tz=LOCAL_TZ).normalize() + pd.tseries.offsets.Day(1)

    start_t = start_t.tz_localize(None).normalize()
    end_t = end_t.tz_localize(None).normalize()
    pool = multiprocessing.Pool(processes=2)
    pool.map(update_esios, pd.date_range(start_t, end_t, freq="D"))


if __name__ == "__main__":
    main()
