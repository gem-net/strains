from collections import OrderedDict

import pandas as pd
from flask import redirect, url_for, render_template, flash, abort, \
    current_app, request, session
from flask_login import login_user, logout_user,\
    current_user, login_required
import bokeh.client as bk_client
import bokeh.embed as bk_embed

from oauth import app, db, OAuthSignIn, MEMBERS_DICT
from .admin import get_members_dict
from .config import table_cols
from .models import User, Strain, Request
from .forms import StrainForm, RequestForm


@app.route('/reload')
def load_members_list():
    global MEMBERS_DICT
    if current_user.is_authenticated and current_user.in_cgem:
        MEMBERS_DICT = get_members_dict()
        n_members = len(MEMBERS_DICT)
        msg = 'Members list updated. Currently {} members.'.format(n_members)
        flash(msg, 'message')
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
        flash('You must select a strain for request.', 'error')
        return redirect(url_for('index'))

    # PREV REQUEST?
    prev = Request.query.filter(Request.requester == current_user).order_by(
        Request.creation_time.desc()).first()
    email = prev.preferred_email if prev else current_user.email
    address = prev.delivery_address if prev else ''

    # SHIP REQUEST FORM
    form = RequestForm(email=email, address=address)
    if form.validate_on_submit():
        strain_dict = dict(session.pop('strain'))
        strain = Strain.query.filter_by(lab=strain_dict['lab'],
                                        entry=strain_dict['entry']).first()
        if not strain:
            strain = Strain(**strain_dict)
        rq = Request()
        rq.requester = current_user
        rq.strain = strain
        rq.delivery_address = form.address.data
        rq.preferred_email = form.email.data
        db.session.add(rq)
        db.session.commit()
        flash('Success! Your strain request has been placed. '
              'You will receive confirmation by email.', 'message')
        return redirect(url_for('index'))

    return render_template("basic.html", title='Strain Request',
                           strain_data=session['strain'],
                           form=form)


@app.route('/requests')
@login_required
def list_requests():
    requests = Request.query.order_by(Request.creation_time.desc()).all()
    if not requests:
        flash('There are currently no active requests.', 'error')
        return redirect(url_for('index'))

    rq_cols = ['id', 'strain_lab', 'strain_entry', 'creation_time', 'status']
    strain_cols = ['organism', 'strain', 'plasmid']
    requester_names = [i.requester.display_name for i in requests]
    strains = [i.strain for i in requests]

    od = OrderedDict()
    for col in rq_cols:
        od[col] = [getattr(i, col) for i in requests]
    od['requester'] = requester_names
    for col in strain_cols:
        od[col] = [getattr(i, col) for i in strains]
    df = pd.DataFrame(od)
    df.insert(1, 'strain_id', df['strain_lab'] + '_' + df['strain_entry'])
    df.drop(['strain_lab', 'strain_entry'], axis=1, inplace=True)
    return render_template("requests.html", title='Current Requests',
                           df=df)


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
    global MEMBERS_DICT
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
