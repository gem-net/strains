import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_bootstrap import Bootstrap
from datetime import datetime

from .oauth import OAuthSignIn
from .admin import get_members_dict
from .config import config, table_cols


app = Flask(__name__)
app.config.from_object(config[os.getenv('FLASK_ENV') or 'default'])

db = SQLAlchemy(app)

bootstrap = Bootstrap()
bootstrap.init_app(app)

lm = LoginManager(app)
lm.login_view = 'index'

MEMBERS_DICT = {}


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        current_user.in_cgem = current_user.social_id in MEMBERS_DICT
        # ADJUST EMAIL IF NECESSARY
        if current_user.in_cgem:
            current_user.email = MEMBERS_DICT[current_user.social_id]
        if current_user.email.endswith('@gem-net.net'):
            current_user.in_cgem = True
        db.session.commit()
    #     g.search_form = SearchForm()
    # g.locale = str(get_locale())


@app.before_first_request
def load_members_list():
    global MEMBERS_DICT
    MEMBERS_DICT = get_members_dict()
    print(MEMBERS_DICT)


from oauth import models
from oauth import routes