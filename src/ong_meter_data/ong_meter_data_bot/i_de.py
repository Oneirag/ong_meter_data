"""
Implements a notify() function to send telegram messages informing on car change
"""

from ong_tsdb.client import OngTsdbClient
from ong_utils import LOCAL_TZ, OngTimer
from ong_meter_data import config, logger
import pandas as pd
from ong_meter_data.ong_meter_data_bot.telegram_notifications import OngTelegramBot


def _read_dfs(date_from: pd.Timestamp, db="meter", meter_metric="LecturaContador", meter_sensor="i-de_1h",
              home_metric="general.active_power", home_sensor="mirubee") -> tuple:
    """Reads data from 'date_from' from two ong_tsdb sources: meter (that includes whole consumption) and
    a home sensor (that includes just the home consumption). Meter data comes from a 1h energy cumulative sensor in kWh
    while home sensor comes from a 1s sensor of current power in W"""
    url = config("url")
    read_client = OngTsdbClient(url=url, token=config("read_token"))
    df_meter = read_client.read(db, meter_sensor, date_from, metrics=[meter_metric])
    with OngTimer(msg="Reading data"):
        df_sensor = read_client.read(db, home_sensor, date_from, metrics=[home_metric])
    return df_meter, df_sensor


def get_charger_kwh(periods: int = 3) -> dict:
    """Returns a dict of timestamp: differences between what is read in home sensor and in meter sensor in kWh
    Timestamp is the date of a day D (normalized) and the differences are computed from D-1 at 18pm till D at 6am
    """
    now = pd.Timestamp.now(LOCAL_TZ)
    date_from = (now - pd.offsets.Day(periods)).normalize().replace(hour=18)
    df_meter, df_sensor = _read_dfs(date_from)
    retval = dict()
    for date in pd.date_range(now, periods=periods, freq="-1D", tz=now.tz):
        end_ts = date.normalize().replace(hour=6)
        start_ts = date.normalize().replace(hour=18) - pd.offsets.Day(1)
        df_meter_calc = df_meter[start_ts:end_ts]
        df_meter_calc = df_meter_calc[df_meter_calc.values > 0]
        df_sensor_calc = df_sensor[df_meter_calc.index[0]:df_meter_calc.index[-1]].mean() * \
                         (df_meter_calc.index[-1] - df_meter_calc.index[0]).seconds / 3600 / 1e3
        if len(df_meter_calc) >= 2:
            charger_kwh = (df_meter_calc.max() - df_meter_calc.min()).iloc[0] - df_sensor_calc.iloc[0]
            retval[date.normalize()] = charger_kwh
    # print(retval)
    return retval


def notify(min_hour: int = 6, max_hour: int = 10, threshold_kwh: float = 2.0, lookback_days: int = 1):
    """Checks if current time is included in min_hour to max_hour and if so sends a telegram msg informing
    whether car charged or not. To check it makes sure differences are above threshold
    :param min_hour: min hour to enable notifications. Before this hour (in local_tz) no notifications are sent.
    Defaults to 6
    :param max_hour: max hour to enable notifications. After this hour (in local_tz) no notifications are sent.
    Defaults to 10
    :param threshold_kwh: minimum difference to consider that car has charged (defaults to 2.0)
    :param lookback_days: number of days to check, defaults to 1 (yesterday only)
    """
    if min_hour <= pd.Timestamp.now(tz=LOCAL_TZ).hour <= max_hour:
        chat_id = config("telegram_chat_id", ()) or None
        bot = OngTelegramBot(chat_id=chat_id)
        res = get_charger_kwh(periods=lookback_days)  # Just today
        for day, reading in res.items():
            day_formatted = day.strftime("%Y-%m-%d")
            if pd.isna(reading):
                logger.debug(f"No data available for fecha {day_formatted}")
                bot.send_msg(f"No hay datos para la fecha {day_formatted}")
            elif reading >= threshold_kwh:
                bot.send_msg(f"Coche cargado {reading:.1f}kWh para fecha {day_formatted}")
            else:
                bot.send_msg(f"Coche NO cargado para fecha {day_formatted}. Registrados {reading:.1f}kWh")
    else:
        # Out of 6 to 10 am do nothing
        return


if __name__ == '__main__':
    notify(min_hour=0, max_hour=24)
    # res = get_charger_kwh()
    # print(res)
    # res = read_meter_df()
    # print(res)
