import threading
import requests
import json
import time
import re
from ong_meter_data import logger


class SensorStreamReader:
    """
    - Connects to SSE url and reads all events in a thread
    - Updates self.sensor_data in the thread
    - Has a get_sensor_data() to read current status
    """

    def __init__(self, base_url: str, sensor_id_regex: str = "^sensor-bl0939_(.*)"):
        """
        base_url - url for the events (typically http://DEVICE_NAME.local/events)
        sensor_id_regex - a regex applied to the id of the sensor. Meter broadcasts some signals that are not meter data.
        This regex is uses to filter them out
        """
        self.base_url = base_url
        self.sensor_id_regex = re.compile(sensor_id_regex)

        # Diccionario compartido entre hilos
        self.sensor_data = {}
        self._lock = threading.Lock()          # evita race conditions

        # Señal para detener el hilo
        self._stop_event = threading.Event()

        # Inicia el thread
        self._thread = threading.Thread(target=self._read_stream, daemon=True)
        self._thread.start()

    def _read_stream(self):
        """Runs thread. Connects and processes the stream."""
        headers = {"Accept": "text/event-stream"}

        # Connect with a 10 seconds timeout. In case of fail, retries.
        while not self._stop_event.is_set():
            try:
                with requests.get(self.base_url, stream=True, headers=headers, timeout=10) as resp:
                    resp.raise_for_status()      # Raises exception in case of HTTP error
                    for line in resp.iter_lines():
                        if self._stop_event.is_set():
                            break
                        if not line:
                            continue
                        # SSE: line starts with data, to filter out other events`
                        if line.startswith(b"data: {"):
                            json_str = line.decode("utf-8").replace("data: ", "")
                            try:
                                payload = json.loads(json_str)
                            except json.JSONDecodeError:
                                continue  # corrupted message, ignore it
                            sensor_id = payload.get("id", "")
                            if match:=self.sensor_id_regex.match(sensor_id):
                                sensor_id = match.group(1)
                                value = payload.get("value")
                                with self._lock:
                                    self.sensor_data[sensor_id] = value
                                # Just for debugging
                                # print(time.time())
                                #pprint.pprint(self.sensor_data)
            except (requests.RequestException, Exception) as exc:
                # In case of error, retries in 1 second
                logger.error(f"Error reading {self.base_url}: {exc}. Retrying in 1 sec…")
                time.sleep(1)

    def get_sensor_data(self):
        """Returns a copy of self.sensor_data."""
        with self._lock:
            return dict(self.sensor_data)

    def stop(self):
        """Stop thread and closes connection."""
        self._stop_event.set()
        self._thread.join(timeout=2)

if __name__ == "__main__":
    DEVICE_NAME = "seeedstudio-2ch-em.local"
    device_name = DEVICE_NAME
    reader = SensorStreamReader(device_name)

    try:
        while True:
            # Main loop
            data = reader.get_sensor_data()
            if data:
                print(f"Current data: {data}")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        reader.stop()