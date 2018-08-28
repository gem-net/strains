import os
from dotenv import load_dotenv
from collections import OrderedDict

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

table_cols = OrderedDict([
    ('lab', {'width': 70}),
    ('entry', {'width': 38}),
    ('organism', {'width': 60}),
    ('strain', {'width': 80}),
    ('plasmid', {'width': 165}),
    ('marker1', {'width': 55}),
    ('marker2', {'width': 55}),
    ('origin', {'width': 55}),
    ('origin2', {'width': 45}),
    ('promoter', {'width': 60}),
    ('benchling_url', {'width': 90}),
    ('desc', {'width': 320}),
    ('submitter', {'width': 70})])


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    APP_URL = os.environ.get('APP_URL')
    SERVER_NAME = os.environ.get('SERVER_NAME')

    OAUTH_CREDENTIALS = {
        'google': {
            'id': os.environ.get('GOOGLE_CLIENT_ID'),
            'secret': os.environ.get('GOOGLE_SECRET')
        }
    }
    DB_CNF = os.environ.get('DB_CNF')
    DB_HOST = os.environ.get('DB_HOST')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # recycle connection before mysql default 8hr wait timeout
    SQLALCHEMY_POOL_RECYCLE = int(
        os.environ.get('SQLALCHEMY_POOL_RECYCLE', 3600))

    SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_FILE')
    GROUP_KEY = os.environ.get('GROUP_KEY')
    SCOPES = ['https://www.googleapis.com/auth/admin.directory.group.member.readonly']


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL_DEV') or \
        'sqlite:///' + os.path.join(basedir, 'db.sqlite')
    DB_NAME = os.environ.get('DB_NAME_DEV')
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO') == 'True'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')
    DB_NAME = os.environ.get('DB_NAME')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
