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
from django.utils.translation import ugettext_noop as _
from geonode.notifications_helper import NotificationsAppConfigBase


class GeoStoriesAppConfig(NotificationsAppConfigBase):
    name = 'geonode.geostories'
    NOTIFICATIONS = (("geostory_created", _("Geostory Created"), _("A Geostory was created"),),
                     ("geostory_updated", _("Geostory Updated"), _("A Geostory was updated"),),
                     ("geostory_approved", _("Geostory Approved"), _("A Geostory was approved by a Manager"),),
                     ("geostory_published", _("Geostory Published"), _("A Geostory was published"),),
                     ("geostory_deleted", _("Geostory Deleted"), _("A Geostory was deleted"),),
                     ("geostory_comment", _("Comment on Geostory"), _("A Geostory was commented on"),),
                     ("geostory_rated", _("Rating for Geostory"), _("A rating was given to a Geostory"),),
                     )


default_app_config = 'geonode.geostories.GeoStoriesAppConfig'
