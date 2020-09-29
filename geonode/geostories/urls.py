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

from django.conf.urls import url
from django.views.generic import TemplateView

from geonode.maps.views import new_map
from geonode.monitoring import register_url_event

geostories_list = register_url_event()(TemplateView.as_view(template_name='geostories/geostories_list.html'))
new_geostory_view = new_map

urlpatterns = [
    # 'geonode.geostories.views',
    url(r'^$',
        geostories_list,
        {'facet_type': 'geostories'},
        name='geostories_browse'),
    url(r'^new$', new_geostory_view, name="new_geostory"),
]
