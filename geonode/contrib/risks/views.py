#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import logging

from django.conf import settings
from django.views.generic import TemplateView, View
from django.core.urlresolvers import reverse


from geonode.utils import json_response
from geonode.contrib.risks.models import (HazardType, AnalysisType,
                                          AdministrativeDivision, RiskAnalysis,
                                          DymensionInfo,
                                          RiskAnalysisDymensionInfoAssociation)

from geonode.contrib.risks.datasource import GeoserverDataSource

cost_benefit_index = TemplateView.as_view(template_name='risks/cost_benefit_index.html')

log = logging.getLogger(__name__)


class FeaturesSource(object):

    AXIS_X = 'x'
    AXIS_Y = 'y'
    KWARGS_MAPPING = {'loc': 'adm_code',
                      'ht': 'hazard_type'}


    def url_kwargs_to_query_params(self, **kwargs):
        out = {}
        for k, v in kwargs.iteritems():
            if self.KWARGS_MAPPING.get(k):
                new_k = self.KWARGS_MAPPING[k]
                out[new_k] = v
        return out

    def get_dim_association(self, analysis, dyminfo):
        ass_list = RiskAnalysisDymensionInfoAssociation.objects.filter(riskanalysis=analysis, dymensioninfo=dyminfo)
        dim_list = set([a.axis_to_dim() for a in ass_list])
        if len(dim_list) != 1:
            raise ValueError("Cannot query more than one dimension at the moment, got {}".format(len(dim_list)))

        return (ass_list.first(), list(dim_list)[0])

    def get_dymlist_field_mapping(self, analysis, dimension, dymlist):
        out = []
        layers = []
        current_dim_name = self.get_dim_association(analysis, dimension)[1]
        out.append(current_dim_name)
        for dym in dymlist:
            if dym != dimension:
                dim_association = self.get_dim_association(analysis, dym)
                if dim_association[0].layer:
                    layers.append(dim_association[0].layer.typename)
                out.append(dim_association[1])
        return (out, layers)

    def get_features(self, analysis, dimension, dymlist, **kwargs):

        (dymlist_to_fields, dym_layers) = self.get_dymlist_field_mapping(analysis, dimension, dymlist)

        s = settings.OGC_SERVER['default']
        gs = GeoserverDataSource('{}/wfs'.format(s['LOCATION'].strip("/")),
                                 username=s['USER'],
                                 password=s['PASSWORD'])
        dim_name = dymlist_to_fields[0]
        layer_name = dym_layers[0]

        features = gs.get_features(layer_name, dim_name, **kwargs)
        return features


class RiskDataExtractionView(FeaturesSource, TemplateView):

    template_name = 'risks/risk_data_extraction_index.html'

risk_data_extraction_index = RiskDataExtractionView.as_view()


class LocationSource(object):
    def get_location(self, **kwargs):
        try:
            loc = AdministrativeDivision.objects.get(code=kwargs['loc'])
        except AdministrativeDivision.DoesNotExist:
            return
        locations = loc.get_parents_chain() + [loc]
        return locations

class LocationView(LocationSource, View):

    def get(self, request, *args, **kwargs):
        locations = self.get_location(**kwargs)
        if not locations:
            return json_response(errors=['Invalid location code'], status=404)
        loc = locations[-1]
        risk_analysis = loc.riskanalysis_set.all()
        hazard_types = HazardType.objects.all()

        print(hazard_types)
        location_data = {'navItems': [location.export() for location in locations],
                         'overview': [ht.set_location(loc).export() for ht in hazard_types]}

        return json_response(location_data)


class HazardTypeView(LocationSource, View):
    """ 
        loc/AF/ht/EQ/"
{
 "navItems": [{
  "label": "Afghanistan",
  "href": "http://disasterrisk-af.geo-solutions.it/risks/risk_data_extraction/loc/AF/ht/EQ/at/loss_impact/"
 }, {
  "label": "Badakhshan",
  "href": "http://disasterrisk-af.geo-solutions.it/risks/risk_data_extraction/loc/AF15/ht/EQ/at/loss_impact/",
 }],
 "overview": [{
  "mnemonic": "EQ",
  "title": "Earthquake",
  "riskAnalysis": 2,
  "href": "http://disasterrisk-af.geo-solutions.it/risks/risk_data_extraction/loc/AF15/ht/EQ/at/loss_impact/",
 }, {
  "mnemonic": "FL",
  "title": "River Flood",
  "riskAnalysis": 0,
  "href": "http://disasterrisk-af.geo-solutions.it/risks/risk_data_extraction/loc/AF15/ht/FL/at/loss_impact/"
 }],
    "hazardType": {
        "mnemonic": "EQ",
        "description": "Lorem ipsum dolor, .....",
        "analysisTypes"[{
            "name": "loss_impact",
            "title": "Loss Impact",
            "href": "http://disasterrisk-af.geo-solutions.it/risks/risk_data_extraction/loc/AF15/ht/EQ/at/loss_impact/"
        }, {
            "name": "impact",
            "title": "Impact Analysis",
            "href": "http://disasterrisk-af.geo-solutions.it/risks/risk_data_extraction/loc/AF15/ht/EQ/at/impact/"
        }]
    },
    "analysisType":{
        "name": "impact",
        "description": "Lorem ipsum dolor, .....",
        "riskAnalysis": [{
            "name": "WP6_future_proj_Hospital",
            "hazardSet": {
                "title": "Afghanistan Hazard-Exposures for provinces and districts for affected hospitals in future projections for SSPs 1-5 in 2050.",
                "abstract": "This table shows the aggregated results of affected hospitals for the Afghanistan districts and provinces from 1km resolution results in the locations over PGA=0.075g. These are measured in USD. The results are created as future projections for SSPs 1-5 in 2050.",
                "category": "economic",
                "fa_icon": "fa_economic"
            },
            "href": "http://disasterrisk-af.geo-solutions.it/risks/risk_data_extraction/loc/AF15/ht/EQ/at/impact/an/1/"
        }, {
            ...,
            "href": "http://disasterrisk-af.geo-solutions.it/risks/risk_data_extraction/loc/AF15/ht/EQ/at/impact/an/2/"
        }
        ]
    }



    """

    def get_hazard_type(self, location, **kwargs):
        try:
            return HazardType.objects.get(mnemonic=kwargs['ht']).set_location(location)
        except (KeyError, HazardType.DoesNotExist,):
            return

    def get_analysis_type(self, location, hazard_type, **kwargs):

        atypes = hazard_type.get_analysis_types()
        if not atypes.exists():
            return None, None,
        if not kwargs.get('at'):
            atype = atypes.first().set_location(location).set_hazard_type(hazard_type)
        else:
            atype = atypes.get(name=kwargs['at']).set_location(location).set_hazard_type(hazard_type)
        return atype, atypes,


    def get(self, request, *args, **kwargs):
        locations = self.get_location(**kwargs)
        if not locations:
            return json_response(errors=['Invalid location code'], status=404)
        loc = locations[-1]
        risk_analysis = loc.riskanalysis_set.all()
        hazard_types = HazardType.objects.all()

        hazard_type = self.get_hazard_type(loc, **kwargs)

        if not hazard_type:
            return json_response(errors=['Invalid hazard type'], status=404)

        (atype, atypes,) = self.get_analysis_type(loc, hazard_type, **kwargs)
        if not atype:
            return json_response(errors=['No analysis type available for location/hazard type'], status=404)

        
        out = {'navItems': [location.export() for location in locations],
                'overview': [ht.set_location(loc).export() for ht in hazard_types],
                'hazardType': hazard_type.get_hazard_details(),
                'analysisType': atype.get_analysis_details()}

        return json_response(out)


class DataExtractionView(FeaturesSource, HazardTypeView):
    """

{
    "riskAnalysisData": {
        "name": "",
        "descriptorFile": "",
        "dataFile": "",
        "metadataFile": "",
        "hazardSet": {
            "title": "",
            "abstract": "",
            "purpose": "",
            "category": "",
            ... other metadata ...
        },
        "data": {
            "dimensions": [
                {
                    "name": "Scenario",
                    "abstract": "Lorem ipsum dolor,...",
                    "unit": "NA",
                    "values": [
                        "Hospital",
                        "SSP1",
                        "SSP2",
                        "SSP3",
                        "SSP4",
                        "SSP5"
                    ]
                },
                {
                    "name": "Round Period",
                    "abstract": "Lorem ipsum dolor,...",
                    "unit": "Years",
                    "values": [
                        "10",
                        "20",
                        "50",
                        "100",
                        "250",
                        "500",
                        "1000",
                        "2500"
                    ]
                }
            ],
            "values":[
                ["Hospital","10",0.0],
                ["Hospital","20",0.0],
                ["Hospital","50",0.0],
                ["Hospital","100",0.0],
                ["Hospital","250",6000000.0],
                ["Hospital","500",6000000.0],
                ["Hospital","1000",6000000.0],
                ["Hospital","2500",6000000.0],

                ["SSP1","10",0.0],
                ["SSP1","20",0.0],
                ["SSP1","50",0.0],
                ["SSP1","100",64380000.0],
                ["SSP1","250",64380000.0],
                ["SSP1","500",64380000.0],
                ["SSP1","1000",64380000.0],
                ["SSP1","2500",64380000.0],

                ...
            ]
        }
    }
}

    """

    def reformat_features(self, risk, dimension, dimensions, features):
        """
        Returns risk data as proper structure

        """
        values = []
        _fields = [self.get_dim_association(risk, dimension)] +\
                  [self.get_dim_association(risk, dim) for dim in dimensions if dim.id != dimension.id]

        fields = ['{}_value'.format(f[1]) for f in _fields]
        
        for feat in features:
            p = feat['properties']
            line = []
            [line.append(p[f]) for f in fields]
            line.append(p['value'])
            values.append(line)

        out = {'dimensions': [dim.set_risk_analysis(risk).export() for dim in dimensions], 
               'values': values}

        return out

    def get(self, request, *args, **kwargs):
        
        locations = self.get_location(**kwargs)
        if not locations:
            return json_response(errors=['Invalid location code'], status=404)
        loc = locations[-1]
        risk_analysis = loc.riskanalysis_set.all()
        hazard_types = HazardType.objects.all() #filter(riskanalysis_hazardtype__in=risk_analysis).distinct()

        hazard_type = self.get_hazard_type(loc, **kwargs)

        if not hazard_type:
            return json_response(errors=['Invalid hazard type'], status=404)

        (atype, atypes,) = self.get_analysis_type(loc, hazard_type, **kwargs)
        if not atype:
            return json_response(errors=['No analysis type available for location/hazard type'], status=404)
       
        risks = atype.get_risk_analysis_list(id=kwargs['an'])
        if not risks:
            return json_response(errors=['No risk analysis found for given parameters'], status=404)
        risk = risks[0]
        
        out = {'riskAnalysisData': risk.get_risk_details()}
        dymlist = risk.dymension_infos.all().distinct()
        if kwargs.get('dym'):
            dimension = dymlist.get(id=kwargs['dym'])
        else:
            dimension = dymlist.filter(riskanalysis_associacion__axis=self.AXIS_X).distinct().get()
         
        feat_kwargs = self.url_kwargs_to_query_params(**kwargs)
        feat_kwargs['risk_analysis'] = risk.name
        features = self.get_features(risk, dimension, dymlist, **feat_kwargs)
        out['riskAnalysisData']['data'] = self.reformat_features(risk, dimension, dymlist, features['features'])

        return json_response(out)



location_view = LocationView.as_view()
hazard_type_view = HazardTypeView.as_view()
analysis_type_view = HazardTypeView.as_view()
data_extraction = DataExtractionView.as_view()
