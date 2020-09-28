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

"""Custom account adapters for django-allauth.

These are used in order to extend the default authorization provided by
django-allauth.

"""

import logging

from allauth.account.utils import user_field
from allauth.account.adapter import get_adapter as get_account_adapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from django.conf import settings
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.module_loading import import_string

# from django.contrib.auth.models import Group
from geonode.groups.models import GroupProfile, GroupMember

from .models import WSO2Department

logger = logging.getLogger(__name__)


def get_data_extractor(provider_id):
    """Get the relevant profile extractor instance for the provider

    Retrieve the data extractor instance to use for getting profile
    information from social account providers.

    """

    extractors = getattr(settings, "SOCIALACCOUNT_PROFILE_EXTRACTORS", {})
    extractor_path = extractors.get(provider_id)
    if extractor_path is not None:
        extractor_class = import_string(extractor_path)
        extractor = extractor_class()
    else:
        extractor = None
    return extractor


def update_profile(sociallogin):
    """Update a people.models.Profile object with info from the sociallogin"""
    user = sociallogin.user
    extractor = get_data_extractor(sociallogin.account.provider)
    if extractor is not None:
        profile_fields = (
            "username",
            "email",
            "area",
            "city",
            "country",
            "delivery",
            "fax",
            "first_name",
            "last_name",
            "organization",
            "position",
            "profile",
            "voice",
            "zipcode",
            "preferred_username",
            "employee_number",
            "fiscal_code",
            "department",
            "authmethod",
            "isdirigente"
        )
        for field in profile_fields:
            try:
                extractor_method = getattr(
                    extractor, "extract_{}".format(field))
                value = extractor_method(sociallogin.account.extra_data)
                if not user_field(user, field):
                    user_field(user, field, value)
            except (AttributeError, NotImplementedError):
                pass  # extractor doesn't define a method for extracting field
    return user


class WSO2AccountAdapter(DefaultSocialAccountAdapter):
    """Customizations for social accounts

    Check `django-allauth's documentation`_ for more details on this class.

    .. _django-allauth's documentation:
         http //django-allauth.readthedocs.io/en/latest/advanced.html#creating-and-populating-user-instances

    """

    def is_open_for_signup(self, request, sociallogin):
        return _site_allows_signup(request)

    def populate_user(self, request, sociallogin, data):
        """This method is called when a new sociallogin is created"""
        user = super(WSO2AccountAdapter, self).populate_user(
            request, sociallogin, data)
        update_profile(sociallogin)
        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login. In case of auto-signup,
        the signup form is not available.
        """
        user = sociallogin.user
        user.set_unusable_password()
        if form:
            get_account_adapter().save_user(request, user, form)
        elif not user.username:
            get_account_adapter().populate_username(request, user)
        sociallogin.save(request)
        extractor = get_data_extractor(sociallogin.account.provider)
        try:
            keywords = extractor.extract_keywords(sociallogin.account.extra_data)
            for _kw in keywords:
                user.keywords.add(_kw)
        except (AttributeError, NotImplementedError):
            pass  # extractor doesn't define a method for extracting field

        user.is_active = True
        if settings.ACCOUNT_APPROVAL_REQUIRED:
            # Check wether the user is active or not
            user.is_active = False

        if user.employee_number in 'CESSATO' or not user.department:
            # Check wether the user belongs to an allowed department or not
            user.is_active = False

        if not WSO2Department.objects.filter(name=user.department).count():
            user.is_active = False
        else:
            groupprofile = GroupProfile.objects.filter(slug=user.department).first()
            if groupprofile:
                groupprofile.join(user)
                if user.isdirigente:
                    GroupMember.objects.get(
                        group=groupprofile, user=user).promote()
                else:
                    GroupMember.objects.get(
                        group=groupprofile, user=user).demote()

        user.save()
        return user

    def respond_user_inactive(self, request, user):
        return _respond_inactive_user(user)


def _site_allows_signup(django_request):
    if getattr(settings, "ACCOUNT_OPEN_SIGNUP", True):
        result = True
    else:
        try:
            result = bool(django_request.session.get("account_verified_email"))
        except AttributeError:
            result = False
    return result


def _respond_inactive_user(user):
    return HttpResponseRedirect(
        reverse("moderator_contacted", kwargs={"inactive_user": user.id})
    )
