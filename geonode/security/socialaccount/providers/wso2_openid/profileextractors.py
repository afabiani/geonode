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
import ast
from geonode.people.profileextractors import BaseExtractor


class WSO2ProfileExtractor(BaseExtractor):

    def extract_email(self, data):
        return data.get("email", "")

    def extract_first_name(self, data):
        return data.get("first_name", "")

    def extract_last_name(self, data):
        return data.get("last_name", "")

    def extract_country(self, data):
        country = data.get("country", "")
        if country:
            from geonode.base.enumerations import COUNTRIES
            for _cnt in COUNTRIES:
                if country == _cnt[1]:
                    country = _cnt[0]
                    break
        return country

    def extract_language(self, data):
        language = data.get("language", "")
        if language:
            from .languages import LANGUAGES
            for _cnt in LANGUAGES:
                if language == _cnt[1]:
                    language = _cnt[0]
                    break
        return language

    def extract_timezone(self, data):
        timezone = data.get("timezone", "")
        if timezone:
            from .timezones import TIMEZONES
            for _cnt in TIMEZONES:
                if timezone == _cnt[1]:
                    timezone = _cnt[0]
                    break
        return timezone

    def extract_city(self, data):
        return data.get("city", "")

    def extract_zipcode(self, data):
        return data.get("postal_code", "")

    def extract_organization(self, data):
        return data.get("organization", "")

    def extract_voice(self, data):
        return data.get("phone", "")

    def extract_groups(self, data):
        return data.get("groups", "")

    def extract_roles(self, data):
        return data.get("roles", "")

    def extract_keywords(self, data):
        return data.get("keywords", "")

    def extract_preferred_username(self, data):
        return data.get("preferred_username", "")

    def extract_employee_number(self, data):
        return data.get("employee_number", "")

    def extract_fiscal_code(self, data):
        return data.get("fiscal_code", "")

    def extract_department(self, data):
        return data.get("department", "")

    def extract_authmethod(self, data):
        return data.get("authmethod", "")

    def extract_isdirigente(self, data):
        return ast.literal_eval(data.get("isdirigente", "False").capitalze())
