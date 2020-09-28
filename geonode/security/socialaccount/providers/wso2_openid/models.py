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
import logging
from uuid import uuid4

# from django.conf import settings
# from django.core.mail import send_mail
from django.db import models
from django.db.models import signals

from django.urls import reverse
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.signals import user_logged_in, user_logged_out

from allauth.socialaccount.signals import social_account_added

from geonode.groups.models import GroupProfile
from geonode.people.models import Profile as GeoNodeProfile, ProfileUserManager
from geonode.people.utils import format_address
from geonode.people.signals import (
    do_login,
    do_logout,
    update_user_email_addresses)

logger = logging.getLogger(__name__)


class WSO2Profile(GeoNodeProfile):

    preferred_username = models.CharField(
        _('Preferred Username'),
        max_length=4096,
        blank=True,
        null=True,
        help_text=_('Preferred Username'))

    employee_number = models.CharField(
        _('Employee Number'),
        max_length=2024,
        blank=True,
        null=True,
        help_text=_('Employee Number'))

    fiscal_code = models.CharField(
        _('Fiscal Code'),
        max_length=32,
        blank=True,
        null=True,
        help_text=_('Fiscal Code'))

    department = models.CharField(
        _('Department'),
        max_length=4096,
        blank=True,
        null=True,
        help_text=_('Department'))

    authmethod = models.CharField(
        _('AUTHMETHOD'),
        max_length=4096,
        blank=True,
        null=True,
        help_text=_('AUTHMETHOD'))

    isdirigente = models.BooleanField(
        _('ISDIRIGENTE'),
        default=False,
        help_text=_('ISDIRIGENTE'))

    def __init__(self, *args, **kwargs):
        super(WSO2Profile, self).__init__(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('profile_detail', args=[self.username, ])

    def __unicode__(self):
        return u"%s" % (self.username)

    def class_name(value):
        return value.__class__.__name__

    objects = ProfileUserManager()
    USERNAME_FIELD = 'username'

    def group_list_public(self):
        return GroupProfile.objects.exclude(
            access="private").filter(groupmember__user=self)

    def group_list_all(self):
        return GroupProfile.objects.filter(groupmember__user=self).distinct()

    def is_member_of_group(self, group_slug):
        """
        Returns if the Profile belongs to a group of a given slug.
        """
        return self.groups.filter(name=group_slug).exists()

    def keyword_list(self):
        """
        Returns a list of the Profile's keywords.
        """
        return [kw.name for kw in self.keywords.all()]

    @property
    def name_long(self):
        if self.first_name and self.last_name:
            return '%s %s (%s)' % (self.first_name,
                                   self.last_name, self.username)
        elif (not self.first_name) and self.last_name:
            return '%s (%s)' % (self.last_name, self.username)
        elif self.first_name and (not self.last_name):
            return '%s (%s)' % (self.first_name, self.username)
        else:
            return self.username

    @property
    def location(self):
        return format_address(self.delivery, self.zipcode,
                              self.city, self.area, self.country)

    def save(self, *args, **kwargs):
        super(WSO2Profile, self).save(*args, **kwargs)
        self._notify_account_activated()
        self._previous_active_state = self.is_active

    def _notify_account_activated(self):
        """Notify user that its account has been activated by a staff member"""
        became_active = self.is_active and not self._previous_active_state
        if became_active and self.last_login is None:
            try:
                # send_notification(users=(self,), label="account_active")

                from invitations.adapters import get_invitations_adapter
                current_site = Site.objects.get_current()
                ctx = {
                    'username': self.username,
                    'current_site': current_site,
                    'site_name': current_site.name,
                    'email': self.email,
                    'inviter': self,
                }

                email_template = 'pinax/notifications/account_active/account_active'

                get_invitations_adapter().send_mail(
                    email_template,
                    self.email,
                    ctx)
            except BaseException:
                import traceback
                traceback.print_exc()


class WSO2Department(models.Model):

    name = models.CharField(
        _('Department Name'),
        max_length=4096,
        blank=False,
        null=False,
        help_text=_('Department Name'))

    label = models.CharField(
        _('Department Label'),
        max_length=4096,
        blank=True,
        null=True,
        help_text=_('Department Label'))

    is_allowed = models.BooleanField(
        _('Department is Allowed'),
        default=True,
        help_text=_('Department is Allowed'))

    class Meta:
        ordering = ("name",)
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'


# def profile_pre_save(instance, sender, **kw):
#     matching_profiles = WSO2Profile.objects.filter(id=instance.id)
#     if matching_profiles.count() == 0:
#         return
#     if instance.is_active and not matching_profiles.get().is_active:
#         # send_notification((instance,), "account_active")
#         if not instance.approved:
#             instance.approved = True
#             message = email_format.format(instance.username, settings.SITEURL, settings.SITEURL,
#                                           instance.username, settings.SITEURL, settings.SITEURL)
#             try:
#                 send_mail(
#                     email_subject,
#                     message,
#                     settings.DEFAULT_FROM_EMAIL,
#                     [instance.email],
#                     fail_silently=True,
#                 )
#             except BaseException:
#                 import traceback
#                 traceback.print_exc()


def profile_post_save(instance, sender, **kwargs):
    """
    Make sure the user belongs by default to the anonymous group.
    This will make sure that anonymous permissions will be granted to the new users.
    """
    from django.contrib.auth.models import Group
    anon_group, created = Group.objects.get_or_create(name='anonymous')
    instance.groups.add(anon_group)
    # do not create email, when user-account signup code is in use
    if getattr(instance, '_disable_account_creation', False):
        return


def department_post_save(instance, sender, **kwargs):
    """
    Make sure a GroupProfile is connected to the Department
    """
    group_name = instance.name
    group_title = instance.label or instance.name
    logger.debug("Creating %s WSO2 Linked Group Profile" % group_name)
    groupprofile, created = GroupProfile.objects.get_or_create(
        slug=group_name)
    if created:
        groupprofile.slug = group_name
        groupprofile.title = group_title
        groupprofile.access = "public_invite"
        groupprofile.save()


def department_post_delete(instance, sender, **kwargs):
    """
    Make sure a GroupProfile is connected to the Department
    """
    group_name = instance.name
    logger.debug("Deleting %s WSO2 Linked Group Profile" % group_name)
    GroupProfile.objects.filter(slug=group_name).delete()


""" Connect relevant signals to their corresponding handlers. """
user_logged_in.connect(do_login)

user_logged_out.connect(do_logout)

social_account_added.connect(
    update_user_email_addresses,
    dispatch_uid=str(uuid4()),
    weak=False
)

# signals.pre_save.connect(
#     profile_pre_save,
#     sender=WSO2Profile
# )

signals.post_save.connect(
    profile_post_save,
    sender=WSO2Profile
)

signals.post_save.connect(
    department_post_save,
    sender=WSO2Department
)

signals.post_delete.connect(
    department_post_delete,
    sender=WSO2Department
)
