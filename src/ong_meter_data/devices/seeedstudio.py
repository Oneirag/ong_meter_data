"""
For seeedstudio dual channel wifi meter
"""
import time
from ong_meter_data.devices.seeed_thread import SensorStreamReader

from ong_meter_data.devices.base import MeteringDevice
from ong_meter_data import logger, timer

class SeeedStudio(MeteringDevice):

    def __init__(self, name, base_url, circuits: tuple, usr="", pwd=""):
        super().__init__(name, base_url, circuits, usr, pwd)
        self.thread_data = SensorStreamReader(base_url)

    def read_meter_url(self):
        """Reads from meter device integrated web server and parses data into self.data """
        data = self.thread_data.get_sensor_data()
        # self.data is a dictionary indexed by metric ("active_power", "voltage", "current", "reactive_power")
        # and data is a list with the same length as circuits
        self.data = {}

        n_circuits = len(self.circuits)
        for raw_metric in "active_power_", "voltage":
            if raw_metric.endswith("_"):
                metrics = [data.get(f"{raw_metric}{idx_circuit+1}") for idx_circuit in range(n_circuits)]
            else:
                metrics = [data.get(raw_metric) for _ in range(n_circuits)]
            if all(metrics):
                metric =raw_metric[:-1] if raw_metric.endswith("_") else raw_metric
                self.data[metric] = metrics

        self.timestamp_ns = time.time_ns()
        logger.debug(f"Leido {self.name} from url {self.base_url}")
        logger.debug(self.data)


if __name__ == '__main__':
    DEVICE_NAME = "seeedstudio-2ch-em.local"

    import requests
    r = requests.get(f"http://{DEVICE_NAME}/events")
    print(r.content())

