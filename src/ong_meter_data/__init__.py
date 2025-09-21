from ong_utils import OngConfig, LOCAL_TZ, create_pool_manager
from pathlib import Path
from ong_tsdb.client import OngTsdbClient
from ong_utils import OngTimer
from functools import lru_cache

__version__ = "0.0.6"

timer = OngTimer(False)
_util = OngConfig("ong_meter_data", cfg_filename="ong_config.yml")
logger = _util.logger
config = _util.config
http = create_pool_manager(None)
add_app_config = _util.add_app_config

# Configuration of the cache file
__COOKIES_FILE = "i-de_cookies.json"
config_file_path = Path("~/.config/ongpi/").expanduser()
config_file_path.mkdir(parents=True, exist_ok=True)
JSON_CONFIG_FILE = config_file_path / __COOKIES_FILE

_bucket = config('bucket')


@lru_cache(maxsize=None)
def init_ongtsdb_client():
    ongtsdb_client = OngTsdbClient(url=config('url'), token=config('admin_token'), validate_server_version=False)
    return ongtsdb_client
