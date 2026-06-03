#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reads meter data from i-DE and stores it into ong_tsdb."""

import logging
import time

import pandas as pd
import schedule

from oligo import Iber
from ong_meter_data import config, logger, LOCAL_TZ
from ong_tsdb.client import OngTsdbClient

_BUCKET = config("bucket")
_SENSORS = [
    {"name": "i-de_consumo_1h", "method": "consumption", "metric": "Consumo"},
    {
        "name": "i-de_facturado_1h",
        "method": "billed_consumption",
        "metric": "ConsumoFacturado",
    },
]


def _month_range(start):
    """Generate monthly periods from start up to now."""
    if isinstance(start, float):
        start = pd.Timestamp.fromtimestamp(start)
    now = pd.Timestamp.now(tz=LOCAL_TZ).normalize()
    start = (
        pd.Timestamp(start, tz=LOCAL_TZ).normalize()
        if start
        else pd.Timestamp("2018-01-01", tz=LOCAL_TZ)
    )
    for when in pd.date_range(
        start.replace(day=1), now + pd.offsets.MonthEnd(1), freq="MS"
    ):
        dt_from = when.normalize().replace(day=1)
        dt_to = (
            dt_from
            + pd.tseries.offsets.MonthEnd(1)
            + pd.tseries.offsets.Day(1)
            - pd.offsets.Second(1)
        )
        yield dt_from, dt_to


def read_historical(iber, client):
    """Fetch historical consumption and write to ong_tsdb."""
    for sensor in _SENSORS:
        last_ts = client.get_lasttimestamp(_BUCKET, sensor["name"])
        for dt_from, dt_to in _month_range(last_ts):
            values = getattr(iber, sensor["method"])(dt_from.date(), dt_to.date())
            if not values:
                continue
            sequence = []
            fecha_dato = dt_from
            for val in values:
                if val is not None:
                    sequence.append(
                        (
                            _BUCKET,
                            sensor["name"],
                            [sensor["metric"]],
                            [float(val)],
                            fecha_dato.value,
                        )
                    )
                fecha_dato += pd.to_timedelta(1, unit="h")
            if sequence:
                client.write(sequence)
                logger.info(
                    f"Historical data for {sensor['name']} in month {dt_from} saved"
                )


def read_current(iber, client):
    """Read instantaneous meter values and write to ong_tsdb."""
    for attempt in range(1, 5):
        try:
            data = iber.measurement()
            meter_reading = float(data.get("meter", -1))
            if meter_reading > 0:
                now_ts = pd.Timestamp.now(tz=LOCAL_TZ).value
                line = f"{_BUCKET},sensor=i-de_consumo_1h LecturaContador={meter_reading} {now_ts}"
                if client.write([line]):
                    logger.info(
                        f"Current meter reading written to ong_tsdb (attempt {attempt})"
                    )
                    return True
            else:
                logger.error(f"Invalid meter reading: {data}")
        except Exception as e:
            logger.error(f"Error reading current meter (attempt {attempt}): {e}")
        time.sleep(attempt * 30)
    return False


def historical_job(client):
    iber = Iber()
    iber.login(user=config("i-de_usr"), password=config("i-de_pwd"))
    read_historical(iber, client)
    logger.info("Historical data read completed")


def main():
    client = OngTsdbClient(
        url=config("url"),
        token=config("admin_token"),
        validate_server_version=False,
    )
    client.create_db(_BUCKET)
    for sensor in _SENSORS:
        client.create_sensor(
            _BUCKET,
            sensor["name"],
            "1h",
            metrics=[sensor["metric"]],
            read_key=config("read_token"),
            write_key=config("write_token"),
        )

    historical_job(client)
    schedule.every().day.at("16:42", "Europe/Madrid").do(historical_job, client)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
