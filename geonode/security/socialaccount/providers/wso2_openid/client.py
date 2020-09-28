# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2020 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################
import requests
from urllib.parse import parse_qsl

from django.utils.http import urlencode

from allauth.socialaccount.providers.oauth2.client import (
    OAuth2Client,
    OAuth2Error,
)


class WSO2OAuth2Client(OAuth2Client):

    def get_redirect_url(self, authorization_url, extra_params):
        params = {
            'client_id': self.consumer_key,
            'redirect_uri': self.callback_url,
            'scope': self.scope,
            'response_type': 'code'
        }
        if self.state:
            params['state'] = self.state
        params.update(extra_params)
        return '%s?%s' % (authorization_url, urlencode(params))

    def get_access_token(self, code):
        data = {
            'redirect_uri': self.callback_url,
            'grant_type': 'authorization_code',
            'code': code}
        if self.basic_auth:
            auth = requests.auth.HTTPBasicAuth(
                self.consumer_key,
                self.consumer_secret)
        else:
            auth = None
            data.update({
                'client_id': self.consumer_key,
                # 'client_secret': self.consumer_secret
            })
        params = None
        self._strip_empty_keys(data)
        url = self.access_token_url
        if self.access_token_method == 'GET':
            params = data
            data = None
        # TODO: Proper exception handling
        resp = requests.request(
            self.access_token_method,
            url,
            params=params,
            data=data,
            headers=self.headers,
            auth=auth)

        access_token = None
        if resp.status_code in [200, 201]:
            # Weibo sends json via 'text/plain;charset=UTF-8'
            if (resp.headers['content-type'].split(
                    ';')[0] == 'application/json' or resp.text[:2] == '{"'):
                access_token = resp.json()
            else:
                access_token = dict(parse_qsl(resp.text))
        if not access_token or 'access_token' not in access_token:
            raise OAuth2Error('Error retrieving access token: %s'
                              % resp.content)

        return access_token

    def _strip_empty_keys(self, params):
        """Added because the Dropbox OAuth2 flow doesn't
        work when scope is passed in, which is empty.
        """
        keys = [k for k, v in params.items() if v == '']
        for key in keys:
            del params[key]
