from ong_utils import OngConfig, LOCAL_TZ, http
import urllib3
import certifi

_util = OngConfig("ong_meter_data", cfg_filename="ong_config.yml")
logger = _util.logger
config = _util.config
# Initialize urllib3 with SSL security enabled
urllib3.contrib.pyopenssl.inject_into_urllib3()
http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',
                           ca_certs=certifi.where(),
                           )
