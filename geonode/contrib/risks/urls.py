#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.conf.urls import url, include

from geonode.contrib.risks import views
from geonode.contrib.risks import geometry_views

extraction_urls = [
    url(r'^$', views.risk_data_extraction_index, name='data_extraction_index'),
    url(r'loc/(?P<loc>[\w\-]+)/$', views.location_view, name='location'),
    url(r'loc/(?P<loc>[\w\-]+)/ht/(?P<ht>[\w\-]+)/$', views.hazard_type_view, name='hazard_type'),
    url(r'loc/(?P<loc>[\w\-]+)/ht/(?P<ht>[\w\-]+)/at/(?P<at>[\w\-]+)/$', views.hazard_type_view, name='analysis_type'),
    url(r'loc/(?P<loc>[\w\-]+)/ht/(?P<ht>[\w\-]+)/at/(?P<at>[\w\-]+)/an/(?P<an>[\w\-]+)/$', views.data_extraction, name='data_extraction'),

    url(r'loc/(?P<loc>[\w\-]+)/ht/(?P<ht>[\w\-]+)/at/(?P<at>[\w\-]+)/an/(?P<an>[\w\-]+)/dym/(?P<dym>[\w\-]+)$', views.data_extraction, name='data_extraction_dym'),
]

geometry_urls = [
    url(r'loc/(?P<adm_code>[\w\-]+)/$', geometry_views.administrative_division_view, name='location'),
]


urlpatterns = [
    url(r'^cost_benefit/$', views.cost_benefit_index, name='risks_cost_benefit_index'),
    url(r'^risk_data_extraction/', include(extraction_urls, namespace='risks')),
    url(r'^geom/', include(geometry_urls, namespace="risks-geom")),

]
