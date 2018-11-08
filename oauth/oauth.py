import json

from rauth import OAuth1Service, OAuth2Service
from flask import current_app, url_for, request, redirect, session


class OAuthSignIn(object):
    providers = None

    def __init__(self, provider_name):
        self.provider_name = provider_name
        credentials = current_app.config['OAUTH_CREDENTIALS'][provider_name]
        self.consumer_id = credentials['id']
        self.consumer_secret = credentials['secret']

    def authorize(self):
        pass

    def callback(self):
        pass

    def get_callback_url(self):
        callback_url = url_for('oauth_callback', provider=self.provider_name,
                       _external=True)
        if 'X-Forwarded-Server' in request.headers:
            server_local = request.headers['Host']
            server_public = request.headers['X-Forwarded-Host']
            callback_url = callback_url.replace(server_local, server_public)
        return callback_url


    @classmethod
    def get_provider(self, provider_name):
        if self.providers is None:
            self.providers = {}
            for provider_class in self.__subclasses__():
                provider = provider_class()
                self.providers[provider.provider_name] = provider
        return self.providers[provider_name]


class GoogleSignIn(OAuthSignIn):
    def __init__(self):
        super(GoogleSignIn, self).__init__('google')
        self.service = OAuth2Service(
            name='google',
            client_id=self.consumer_id,
            client_secret=self.consumer_secret,
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            access_token_url='https://www.googleapis.com/oauth2/v3/token',
            base_url='https://people.googleapis.com/v1/'
        )

    def authorize(self):
        return redirect(self.service.get_authorize_url(
            scope='email profile',
            response_type='code',
            redirect_uri=self.get_callback_url())
        )

    def callback(self):
        def decode_json(payload):
            return json.loads(payload.decode('utf-8'))

        if 'code' not in request.args:
            return None, None, None
        oauth_session = self.service.get_auth_session(
            data={'code': request.args['code'],
                  'grant_type': 'authorization_code',
                  'redirect_uri': self.get_callback_url()},
            decoder=decode_json
        )
        me = oauth_session.get('people/me?personFields=emailAddresses,names').json()
        account_id, email_primary, email_list = self.parse_email_addreses(me)
        display_name = self.parse_display_name(me)
        if not display_name:
            display_name = email_primary.split('@')[0]
        return (
            account_id,
            display_name,
            email_primary
        )

    @staticmethod
    def get_primary(vals):
        return [i for i in vals if 'primary' in i['metadata']][0]

    @staticmethod
    def parse_email_addreses(data_dict):
        email_vals = data_dict['emailAddresses']
        primary = GoogleSignIn.get_primary(email_vals)
        account_id = primary['metadata']['source']['id']
        email_primary = primary['value']
        email_list = [i['value'] for i in email_vals]
        return account_id, email_primary, email_list

    @staticmethod
    def parse_display_name(data_dict):
        try:
            names = GoogleSignIn.get_primary(data_dict['names'])
        except KeyError:
            return ''
        return names['displayName']
