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

from datetime import timedelta
from requests import RequestException

from django.utils import timezone
from django.http import HttpResponseRedirect
from django.core.exceptions import PermissionDenied

from openid.extensions.ax import AttrInfo, FetchRequest
from openid.extensions.sreg import SRegRequest

from allauth.utils import get_request_param
from allauth.socialaccount import app_settings
from allauth.socialaccount.models import SocialLogin, SocialToken
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2CallbackView,
    OAuth2LoginView,
)
from allauth.socialaccount.providers.openid.utils import (
    AXAttributes,
    SRegFields,
)
from allauth.socialaccount.providers.base import (
    AuthError,
    ProviderException
)
from allauth.socialaccount.helpers import (
    complete_social_login,
    render_authentication_error,
)

from .client import WSO2OAuth2Client
from .provider import WSO2OpenIDProvider


class WSO2OAuth2Adapter(OAuth2Adapter):
    provider = WSO2OpenIDProvider
    provider_id = WSO2OpenIDProvider.id
    basic_auth = False
    supports_state = True

    settings = app_settings.PROVIDERS.get(provider_id, {})
    provider_base_url = '{0}/'.format(settings.get("WSO2_URL"))

    scope_delimiter = ' '
    access_token_method = "POST"
    access_token_url = '{0}oauth2/token'.format(provider_base_url)
    authorize_url = '{0}oauth2/authorize'.format(provider_base_url)
    profile_url = '{0}oauth2/userinfo'.format(provider_base_url)

    def complete_login(self, request, app, token, response):
        headers = {'Authorization': 'Bearer {0}'.format(token.token)}
        response = requests.post(self.profile_url, headers=headers)
        response.raise_for_status()
        extra_data = response.json()
        extra_data['id'] = extra_data['sub']
        del extra_data['sub']
        return self.get_provider().sociallogin_from_response(
            request,
            extra_data
        )

    def parse_token(self, data):
        token = SocialToken(token=data['access_token'])
        token.token_secret = data.get('refresh_token', '')
        expires_in = data.get(self.expires_in_key, None)
        if expires_in:
            token.expires_at = timezone.now() + timedelta(
                seconds=int(expires_in))
        return token

    def perform_openid_auth(self, form):
        if not form.is_valid():
            return form
        request = self.request
        provider = self.provider(request)
        endpoint = form.cleaned_data['openid']
        client = self.get_client(provider, endpoint)
        realm = self.get_realm(provider)
        auth_request = client.begin(endpoint)
        sreg = SRegRequest()
        for name in SRegFields:
            sreg.requestField(
                field_name=name, required=True
            )
        auth_request.addExtension(sreg)
        ax = FetchRequest()
        for name in AXAttributes:
            ax.add(AttrInfo(name,
                            required=True))
        server_settings = \
            provider.get_server_settings(endpoint)
        extra_attributes = \
            server_settings.get('extra_attributes', [])
        for _, name, required in extra_attributes:
            ax.add(AttrInfo(name,
                            required=required))
        auth_request.addExtension(ax)
        SocialLogin.stash_state(request)
        # Fix for issues 1523 and 2072 (github django-allauth)
        if "next" in form.cleaned_data and form.cleaned_data["next"]:
            auth_request.return_to_args['next'] = \
                form.cleaned_data['next']
        redirect_url = auth_request.redirectURL(
            realm,
            request.build_absolute_uri(self.get_callback_url()))
        return HttpResponseRedirect(redirect_url)


class WSO2OAuth2ClientMixin(object):

    def get_client(self, request, app):
        callback_url = self.adapter.get_callback_url(request, app)
        provider = self.adapter.get_provider()
        scope = provider.get_scope(request)
        client = WSO2OAuth2Client(self.request, app.client_id, app.secret,
                                  self.adapter.access_token_method,
                                  self.adapter.access_token_url,
                                  callback_url,
                                  scope,
                                  scope_delimiter=self.adapter.scope_delimiter,
                                  headers=self.adapter.headers,
                                  basic_auth=self.adapter.basic_auth)
        return client


class WSO2OAuth2LoginView(WSO2OAuth2ClientMixin, OAuth2LoginView):

    def dispatch(self, request):
        response = super(WSO2OAuth2LoginView, self).dispatch(request)
        return response

    # def dispatch(self, request, *args, **kwargs):
    #     provider = self.adapter.get_provider()
    #     app = provider.get_app(self.request)
    #     client = self.get_client(request, app)
    #     action = request.GET.get('action', AuthAction.AUTHENTICATE)
    #     auth_url = self.adapter.authorize_url
    #     auth_params = provider.get_auth_params(request, action)
    #     client.state = SocialLogin.stash_state(request)
    #     try:
    #         return HttpResponseRedirect(client.get_redirect_url(
    #             auth_url, auth_params))
    #     except OAuth2Error as e:
    #         return render_authentication_error(
    #             request,
    #             provider.id,
    #             exception=e)


class WSO2OAuth2CallbackView(WSO2OAuth2ClientMixin, OAuth2CallbackView):

    def dispatch(self, request, *args, **kwargs):
        if 'error' in request.GET or 'code' not in request.GET:
            # Distinguish cancel from error
            auth_error = request.GET.get('error', None)
            if auth_error == self.adapter.login_cancelled_error:
                error = AuthError.CANCELLED
            else:
                error = AuthError.UNKNOWN
            return render_authentication_error(
                request,
                self.adapter.provider_id,
                error=error)
        app = self.adapter.get_provider().get_app(self.request)
        client = self.get_client(request, app)
        try:
            access_token = client.get_access_token(request.GET['code'])
            token = self.adapter.parse_token(access_token)
            token.app = app
            login = self.adapter.complete_login(request,
                                                app,
                                                token,
                                                response=access_token)
            login.token = token
            if self.adapter.supports_state:
                login.state = SocialLogin \
                    .verify_and_unstash_state(
                        request,
                        get_request_param(request, 'state'))
            else:
                login.state = SocialLogin.unstash_state(request)
            return complete_social_login(request, login)
        except (PermissionDenied,
                OAuth2Error,
                RequestException,
                ProviderException) as e:
            return render_authentication_error(
                request,
                self.adapter.provider_id,
                exception=e)


oauth2_login = WSO2OAuth2LoginView.adapter_view(WSO2OAuth2Adapter)
oauth2_callback = WSO2OAuth2CallbackView.adapter_view(WSO2OAuth2Adapter)
