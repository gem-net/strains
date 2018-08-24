from flask import Flask, redirect, url_for, render_template, flash, abort, \
    current_app, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user,\
    current_user, login_required
from flask_bootstrap import Bootstrap
from datetime import datetime

import bokeh.client as bk_client
import bokeh.embed as bk_embed

from .oauth import OAuthSignIn
from .admin import get_members_dict
from .config import Config, table_cols


app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
db.create_all()

bootstrap = Bootstrap()
bootstrap.init_app(app)

lm = LoginManager(app)
lm.login_view = 'index'

MEMBERS_DICT = {}


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    display_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(64), nullable=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    in_cgem = db.Column(db.Boolean, default=False)


@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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


@app.route('/reload')
def load_members_list():
    global MEMBERS_DICT
    if current_user.is_authenticated and current_user.in_cgem:
        MEMBERS_DICT = get_members_dict()
        n_members = len(MEMBERS_DICT)
        msg = 'Members list updated. Currently {} members.'.format(n_members)
        flash(msg, 'success')
        return render_template('reload.html')
    else:
        abort(404)


@app.route('/strains')
@app.route('/')
def index():
    # pull a new session from a running Bokeh server
    url = current_app.config['APP_URL']
    with bk_client.pull_session(url=url) as session:

        # update or customize that session
        # session.document.roots[0].children[
        #     1].title.text = "Special Sliders For A Specific User!"

        # generate a script to load the customized session
        script = bk_embed.server_session(session_id=session.id, url=url)
        # use the script in the rendered page
        return render_template("index.html", script=script,
                               col_names=[i for i in table_cols])



@app.route('/request',  methods=['POST', 'GET'])
@login_required
def request_strain():
    # pull a new session from a running Bokeh server


    return render_template("basic.html", title='Strain Request',
                           col_names=[i for i in table_cols],
                           form=request.form)





@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth_obj = OAuthSignIn.get_provider(provider)
    return oauth_obj.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    oauth_obj = OAuthSignIn.get_provider(provider)
    social_id, username, email = oauth_obj.callback()
    if social_id is None:
        flash('Authentication failed.', 'error')
        return redirect(url_for('index'))
    user = User.query.filter_by(social_id=social_id).first()
    if not user:
        if social_id in MEMBERS_DICT:
            email = MEMBERS_DICT[social_id]
        user = User(social_id=social_id, display_name=username, email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))
