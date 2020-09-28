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
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from geonode.people.models import Profile
from geonode.people.admin import ProfileAdmin

from .models import (
    WSO2Profile,
    WSO2Department
)


@admin.register(WSO2Profile)
class WSO2ProfileAdmin(ProfileAdmin):

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {
            'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('WSO2 Profile Extra Data'), {'fields': ('preferred_username', 'employee_number',
                                                   'fiscal_code', 'department',
                                                   'authmethod', 'isdirigente')}),
        (_('Extended profile'), {'fields': ('organization', 'profile',
                                            'position', 'voice', 'fax',
                                            'delivery', 'city', 'area',
                                            'zipcode', 'country',
                                            'keywords')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name',
                    'is_staff', 'is_active')


@admin.register(WSO2Department)
class WSO2DepartmentAdmin(admin.ModelAdmin):

    list_display = ('name', 'label', 'is_allowed')


admin.site.unregister(Profile)
