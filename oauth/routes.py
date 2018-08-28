from collections import OrderedDict

import pandas as pd
from flask import redirect, url_for, render_template, flash, abort, \
    current_app, request, session
from flask_login import login_user, logout_user,\
    current_user, login_required
import bokeh.client as bk_client
import bokeh.embed as bk_embed

from oauth import app, db, OAuthSignIn, MEMBERS_DICT
from .admin import get_members_dict, get_requests_df
from .config import table_cols
from .models import User, Strain, Request, Comment
from .forms import StrainForm, RequestForm, StatusForm, VolunteerForm, \
    CommentForm


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

    df = get_requests_df(requests)
    return render_template("requests.html", title='Current Requests',
                           df=df, categ="complete")


@app.route('/my-requests')
@login_required
def my_requests():
    requests = Request.query.filter(Request.requester == current_user).\
            order_by(Request.creation_time.desc()).all()
    if not requests:
        flash('You do not have any active requests.', 'error')
        return redirect(url_for('index'))

    df = get_requests_df(requests)

    return render_template("requests.html", title='Current Requests',
                           df=df, categ="mine")


@app.route('/request/<request_id>', methods=['POST', 'GET'])
@login_required
def show_request(request_id):

    rq = Request.query.filter_by(id=request_id).first_or_404()
    strain = rq.strain
    requester = rq.requester

    meta = OrderedDict()
    meta['Strain ID'] = strain.get_strain_id()
    meta['Request Date'] = rq.creation_time
    meta['Request By'] = requester.display_name
    meta['Deliver To'] = rq.delivery_address

    strain_dict = OrderedDict()
    strain_cols = [i for i in table_cols if i not in ['lab', 'entry']]
    for col in strain_cols:
        strain_dict[col] = getattr(strain, col)

    volunteer_form = VolunteerForm(prefix='volunteer-')
    if volunteer_form.submit.data:
        rq.shipper = current_user
        rq.status = 'processing'
        db.session.add(rq)
        db.session.commit()
        flash('Thanks for volunteering to handle this request!', 'message')
        meta['Shipper'] = rq.shipper.display_name

    # STATUS FOLLOWS VOLUNTEER FORM TO ALLOW STATUS UPDATE
    status = rq.status if rq.status != 'unassigned' else 'processing'
    status_form = StatusForm(prefix='status-', status=status)
    if status_form.submit.data and status_form.validate_on_submit():
        old_status = rq.status
        new_status = status_form.status.data
        if old_status != new_status:
            rq.status = new_status
            db.session.add(rq)
            db.session.commit()
            flash('Status changed to {}.'.format(new_status), 'message')
        else:
            flash('Status unchanged: {}.'.format(new_status), 'message')

    comment_form = CommentForm(prefix='comment-')
    if comment_form.submit.data and comment_form.validate_on_submit():
        comment = Comment()
        comment.content = comment_form.content.data
        comment.commenter = current_user
        comment.request = rq
        db.session.add(comment)
        db.session.commit()
        flash('Thanks for your comment!', 'message')

    return render_template("request_single.html", title='Current Requests',
                           meta=meta, rq=rq, strain_dict=strain_dict,
                           status_form=status_form,
                           volunteer_form=volunteer_form,
                           comment_form=comment_form,
                           comments=rq.comments)


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
