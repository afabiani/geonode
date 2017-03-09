#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import json
from StringIO import StringIO
from django.test import Client
from geonode.contrib.risks.models import DymensionInfo
from geonode.contrib.risks.tests import RisksTestCase
from geonode.contrib.risks.tests.smoke import (TESTDATA_FILE_INI, TESTDATA_FILE_DATA,
                                               TEST_RISK_ANALYSIS, TEST_REGION, call_command)


class RisksViewTestCase(RisksTestCase):

    def test_data_views(self):
        """
        Check if data views returns proper data

        """
        out = StringIO()
        call_command('createriskanalysis', descriptor_file=TESTDATA_FILE_INI, stdout=out)
        call_command(
            'importriskdata',
            commit=True,
            excel_file=TESTDATA_FILE_DATA,
            region=TEST_REGION,
            risk_analysis=TEST_RISK_ANALYSIS,
            stdout=out)

        client = Client()
        url = '/risks/risk_data_extraction/loc/INVALID/'
        resp = client.get(url)
        self.assertEqual(resp.status_code, 404)
        data = json.loads(resp.content)
        self.assertFalse(data.get('navItems'))
        self.assertTrue(data.get('errors'))

        url = '/risks/risk_data_extraction/loc/AF/'
        resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get('navItems'))
        self.assertTrue(data.get('overview'))
        self.assertTrue(len(data['overview']) > 0)
        non_empty = []
        for ht in data['overview']:
            url = ht['href']
            resp = client.get(url)
            if ht['riskAnalysis'] > 0:
                non_empty.append(ht['href'])
                self.assertEqual(resp.status_code, 200,
                                 'wrong status on non-empty hazard type {}: {}'.format(url, resp.content))
                data = json.loads(resp.content)
                self.assertTrue(data.get('navItems'))
            else:
                self.assertEqual(resp.status_code, 404,
                                 'wrong status on empty hazard type {}: {}'.format(url, resp.content))
        self.assertTrue(len(non_empty) > 0, "There should be at least one RiskAnalysis available")

        # let's check non-empty hazard types, there should be some risk analysis here!
        for ne in non_empty:
            resp = client.get(url)
            self.assertEqual(resp.status_code, 200,
                             'wrong status on non-empty hazard type {}: {}'.format(url, resp.content))
            data = json.loads(resp.content)
            self.assertTrue(data.get('analysisType'))
            self.assertTrue(data.get('hazardType'))
            self.assertTrue(data['hazardType'].get('analysisTypes'))
            self.assertTrue(data['analysisType'].get('riskAnalysis'))
            for ra in data['analysisType']['riskAnalysis']:
                url = ra['href']
                resp = client.get(url)
                self.assertEqual(resp.status_code, 200,
                                 'wrong status on non-empty hazard type {}: {}'.format(url, resp.content))
                data = json.loads(resp.content)
                self.assertTrue(data.get('riskAnalysisData'))
                self.assertTrue(data['riskAnalysisData'].get('data'))
                for d in data['riskAnalysisData']['data']['dimensions']:
                    self.assertEqual(DymensionInfo.objects.filter(name=d['name']).count(), 1)

                # cannot evaluate
                #self.assertTrue(len(data['riskAnalysisData']['data']['values'])>0)
