from ong_utils import OngConfig, LOCAL_TZ, create_pool_manager

__version__ = "0.0.1"

_util = OngConfig("ong_meter_data", cfg_filename="ong_config.yml")
logger = _util.logger
config = _util.config
http = create_pool_manager(None)
add_app_config = _util.add_app_config
