from collections import OrderedDict

import pandas as pd
from flask import current_app
from google.oauth2 import service_account
from googleapiclient.discovery import build


def get_members_dict():
    """Get dictionary of {google_id: email_address}."""
    SERVICE_ACCOUNT_FILE = current_app.config['SERVICE_ACCOUNT_FILE']
    GROUP_KEY = current_app.config['GROUP_KEY']
    SCOPES = current_app.config['SCOPES']

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    delegated_credentials = credentials.with_subject('stephen@gem-net.net')

    # GET: https://www.googleapis.com/admin/directory/v1/groups/04i7ojhp13c8l10/members
    service = build('admin', 'directory_v1', credentials=delegated_credentials)
    res = service.members().list(groupKey=GROUP_KEY).execute()
    members_dict = dict([(i['id'], i['email']) for i in res['members'] if 'email' in i])
    return members_dict


def get_requests_df(requests):
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
    return df
