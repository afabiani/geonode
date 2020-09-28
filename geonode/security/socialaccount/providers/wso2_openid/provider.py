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
import six
from collections import namedtuple

from allauth.socialaccount import app_settings
from allauth.socialaccount.providers.openid.utils import AXAttribute
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider
from allauth.socialaccount.providers.base import ProviderAccount

OIDCAttribute = namedtuple('OIDCAttribute', 'field uri')

OIDCAttributes = [
    OIDCAttribute('realname', AXAttribute.PERSON_NAME),
    OIDCAttribute('first_name', AXAttribute.PERSON_FIRST_NAME),
    OIDCAttribute('last_name', AXAttribute.PERSON_LAST_NAME),
    OIDCAttribute('email', AXAttribute.CONTACT_EMAIL),
    OIDCAttribute('admin', 'http://axschema.org/identity/isAdmin'),
    OIDCAttribute('groups', 'http://axschema.org/claims/groups'),
    OIDCAttribute('roles', 'http://axschema.org/claims/roles'),
    OIDCAttribute('country', 'http://axschema.org/contact/country/home'),
    OIDCAttribute('organization', 'http://axschema.org/contact/organization'),
    OIDCAttribute('nickname', 'http://axschema.org/namePerson/friendly'),
    OIDCAttribute('birthday', 'http://axschema.org/birthDate'),
    OIDCAttribute('gender', 'http://axschema.org/person/gender'),
    OIDCAttribute('postal_code', 'http://axschema.org/contact/postalCode/home'),
    OIDCAttribute('timezone', 'http://axschema.org/pref/timezone'),
    OIDCAttribute('language', 'http://axschema.org/pref/language'),
    OIDCAttribute('name_prefix', 'http://axschema.org/namePerson/prefix'),
    OIDCAttribute('middle_name', 'http://axschema.org/namePerson/middle'),
    OIDCAttribute('name_suffix', 'http://axschema.org/namePerson/suffix'),
    OIDCAttribute('web', 'http://axschema.org/contact/web/default'),
    OIDCAttribute('thumbnail', 'http://axschema.org/media/image/default'),
    OIDCAttribute('phone', 'http://axschema.org/contact/phone/default'),
]


class WSO2Account(ProviderAccount):

    def to_str(self):
        dflt = super(WSO2Account, self).to_str()
        return self.account.extra_data.get('personaname', dflt)

    def get_profile_url(self):
        return self.account.extra_data.get("profileurl")

    def get_avatar_url(self):
        return (
            self.account.extra_data.get("avatarfull") or
            self.account.extra_data.get("avatarmedium") or
            self.account.extra_data.get("avatar")
        )


def request_wso2_account_summary(api_key, wso2_id, wso2_extra_attrs):
    wso2_account_summary = {"wso2id": wso2_id, "keywords": ["OpenID", "WSO2"]}
    wso_att_keys = {}
    for _key, _value in wso2_extra_attrs.items():
        if _key.startswith('type'):
            _kk = _key.lstrip('type.')
            wso_att_keys[_kk] = _value
    for _key, _attr in wso_att_keys.items():
        for _oidc_attr in OIDCAttributes:
            if _attr == _oidc_attr.uri:
                wso2_account_summary[_oidc_attr.field] = wso2_extra_attrs['value.{}'.format(
                    _key)]
                continue

    return wso2_account_summary


class WSO2OpenIDProvider(OAuth2Provider):
    id = "wso2_openid"
    name = "WSO2"
    settings = app_settings.PROVIDERS.get(id, {})
    account_class = WSO2Account

    def get_method(self):
        return self.get_settings().get('METHOD', 'oauth2')

    def get_default_scope(self):
        return ['openid', ]

    def sociallogin_from_response(self, request, response):
        # ns_uri = self.settings.get("WSO2_NS_URI", 'http://openid.net/srv/ax/1.0')
        # wso2_extra_attrs = response.getSignedNS(ns_uri)
        wso2_extra_attrs = response.copy()
        wso2_id = response["id"]
        wso2_api_key = self.get_app(request).secret
        wso2_extra_attrs.update(request_wso2_account_summary(
            wso2_api_key, wso2_id, wso2_extra_attrs
        ))
        return super(WSO2OpenIDProvider, self).sociallogin_from_response(
            request, wso2_extra_attrs
        )

    def extract_uid(self, response):
        return response["id"]

    def extract_extra_data(self, response):
        return response.copy()

    def extract_common_fields(self, response):
        full_name = response.get("preferred_username", "").strip()
        if full_name.count(" ") == 1:
            first_name, last_name = full_name.split()
        else:
            first_name, last_name = full_name, ""

        first_name = response.get("given_name", first_name).strip()
        last_name = response.get("family_name", last_name).strip()
        email = response.get("email", "").strip()
        country = response.get("country", "").strip()
        organization = response.get("organization", "").strip()

        _common_fields = {
            "username": response["id"],
            "email": email if len(email) > 0 else response["id"],
            "country": country,
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "organization": organization,
        }

        for _key, _value in response.items():
            if _key not in _common_fields:
                _common_fields[_key] = _value.strip() if isinstance(_value, six.string_types) else _value

        return _common_fields


provider_classes = [WSO2OpenIDProvider]
