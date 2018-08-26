from flask import redirect, url_for, render_template, flash, abort, \
    current_app, request, session
from flask_login import login_user, logout_user,\
    current_user, login_required
import bokeh.client as bk_client
import bokeh.embed as bk_embed

from oauth import app, db, OAuthSignIn

from .admin import get_members_dict
from .config import table_cols
from .models import User, Strain
from .forms import StrainForm, RequestForm


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


@app.route('/strains', methods=['POST', 'GET'])
@app.route('/',  methods=['POST', 'GET'])
def index():
    if not (current_user.is_authenticated and current_user.in_cgem):
        return render_template("index.html", script=None, form=None)

    form = StrainForm()  # prefix='ship-'
    if form.validate_on_submit():
        # remember strain object in session, redirect to order form
        strain = [(col, getattr(form, col).data) for col in table_cols]
        session['strain'] = strain
        return redirect(url_for('request_strain'))

    # pull a new session from a running Bokeh server
    url = current_app.config['APP_URL']
    with bk_client.pull_session(url=url) as bk_session:
        # generate a script to load the customized session
        script = bk_embed.server_session(session_id=bk_session.id, url=url)
        # use the script in the rendered page
        return render_template("index.html", script=script, form=form)


@app.route('/request',  methods=['POST', 'GET'])
@login_required
def request_strain():
    if 'strain' not in session:
        redirect(url_for('index'))

    # SHIP REQUEST FORM
    form = RequestForm()
    if form.validate_on_submit():
        strain = Strain(**dict(session['strain']))
        session.pop('strain')
        db.session.add(strain)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template("basic.html", title='Strain Request',
                           strain_data=session['strain'],
                           form=form)


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
