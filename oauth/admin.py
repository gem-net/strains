from google.oauth2 import service_account
from googleapiclient.discovery import build


SERVICE_ACCOUNT_FILE = '/Users/sgg/Dropbox/Townsend/gem-net/sheets_app/cgem-strains-4370c01b1ae8.json'
GROUP_KEY = '04i7ojhp13c8l10'
SCOPES = ['https://www.googleapis.com/auth/admin.directory.group.member.readonly']


def get_members_dict():
    """Get dictionary of {google_id: email_address}."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    delegated_credentials = credentials.with_subject('stephen@gem-net.net')

    # GET: https://www.googleapis.com/admin/directory/v1/groups/04i7ojhp13c8l10/members
    service = build('admin', 'directory_v1', credentials=delegated_credentials)
    res = service.members().list(groupKey=GROUP_KEY).execute()
    members_dict = dict([(i['id'], i['email']) for i in res['members'] if 'email' in i])
    return members_dict
