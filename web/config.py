import os

ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
SRC_DIR = os.path.join(ROOT_DIR, 'src')

import sys
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000
DEBUG = False

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'user_settings.json')

DEFAULT_SETTINGS = {
    "download_dir": os.path.join(os.path.dirname(__file__), '..', 'downloads', 'JMComic'),
    "proxy": "",
    "thread_count_image": 30,
    "thread_count_photo": 5,
    "image_suffix": None,
    "client_impl": "api",
    "retry_times": 5,
    "zip_enabled": True,
    "zip_delete_after": False,
    "jm_username": "",
    "jm_password": "",
    "max_parallel_downloads": 3,
}
