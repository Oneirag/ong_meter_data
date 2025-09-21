#!/usr/bin/python
import time

from ong_meter_data import logger, config, init_ongtsdb_client, _bucket
from ong_meter_data.devices.seeedstudio import SeeedStudio

def combine_url(base, endpoint) -> str:
    """Combines a base_url and an endpoint, avoiding double // that happens when base ends ad endpoint starts by / """
    if base.endswith("/") and endpoint.startswith("/"):
        return base + endpoint[1:]
    else:
        return base + endpoint


meters = dict()
meters["seeedstudio"] = SeeedStudio(
                "seeedstudio",
        base_url="http://seeedstudio-2ch-em.local/events",
        circuits=("general", "lavadora")
)
# meters['mirubee'] = MirubeeDevice('mirubee', base_url="http://mirubee",
#                                   circuits=('general', 'lights'),
#                                   usr=config("meter_user"), pwd=config("meter_pwd")
#                                   )
# meters['smapee'] = SmappeeDevice('smappee', base_url="http://smappee",
#                                   circuits=('general', 'lavadora', 'nevera'),
#                                   usr=config("meter_user"), pwd=config("meter_pwd")
#                                   )
# meters['tinytuya'] = TinyTuyaDevice('tinytuya', base_url=config("tinytuya_wdm_base_url"),
#                                     circuits=('general', 'lavadora'),
#                                     usr=config("tinytuya_wdm_usr"), pwd=config("tinytuya_wdm_pwd")
#                                     )
# meters['tinytuya'] = TuyaCloudDevice('tinytuya', cloud_api_base_url=config("tuyacloud_api_endoint"),
#                                     circuits=('general', 'lavadora'),
#                                     access_id=config("tuyacloud_access_id"), access_key=config("tuyacloud_access_key"),
#                                     device_id=config("tuyacloud_device_id")
#                                     )


# Generate database and sensors, if needed
ongtsdb_client = init_ongtsdb_client()
ongtsdb_client.create_db(_bucket)
for sensor in meters.keys():
    # ongtsdb_client.delete_sensor(_bucket, sensor)
    ongtsdb_client.create_sensor(_bucket, sensor, "1s", metrics=list(),
                                 read_key=config('read_token'), write_key=config('write_token'))

while True:
    start_t = time.time()
    #   if True:
    # threads = [threading.Thread(target=M.read_write_meter) for M in meters.values()]
    # for thread in threads:
    #     thread.start()
    # for thread in threads:
    #     thread.join()

    for M in meters.values():
        try:
            M.read_write_meter()
        except Exception as e:
            logger.error(e)
    logger.debug("Elapsed Time: %s" % (time.time() - start_t))
    SECONDS_SLEEP = 10      # To avoid problems with cloud (previously I used every second)
    time.sleep(max(0.0, start_t + SECONDS_SLEEP - time.time()))
