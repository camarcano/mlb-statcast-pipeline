import os
import sys

PROJECT_DIR = "/var/www/mlb-statcast-pipeline"

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

venv_site = os.path.join(PROJECT_DIR, "venv", "lib", "python3", "site-packages")
if os.path.isdir(venv_site) and venv_site not in sys.path:
    sys.path.insert(0, venv_site)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_DIR, ".env"))

from webapp import create_app

application = create_app("production")
