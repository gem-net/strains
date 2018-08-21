import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config(object):
    CREDS_JSON = os.environ.get('CREDS_JSON')
    FEATHER_PATH = os.environ.get('FEATHER_PATH') or 'df.feather'


