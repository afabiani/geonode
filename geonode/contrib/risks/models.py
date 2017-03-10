# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2017 OSGeo
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

from django.core.urlresolvers import reverse
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from django.core import files
from geonode.base.models import ResourceBase, TopicCategory
from geonode.layers.models import Layer


class Exportable(object):
    EXPORT_FIELDS = []

    def export(self, fieldset=None):
        out = {}
        if fieldset is None:
            fieldset = self.EXPORT_FIELDS
        for fname, fsource in fieldset:
            val = getattr(self, fsource, None)
            if callable(val):
                val = val()
            elif isinstance(val, files.File):
                try:
                    val = val.url
                except ValueError:
                    val = None
            out[fname] = val
        return out


class LocationAware(object):

    # hack to set location context, so we can return
    # location-specific related objects
    def set_location(self, loc):
        self._location = loc
        return self

    def get_location(self):
        if not getattr(self, '_location', None):
            raise ValueError("Cannot use location-less {} here".format(self.__class__.__name__))
        return self._location


class HazardTypeAware(object):
    def set_hazard_type(self, ht):
        self._hazard_type = ht
        return self

    def get_hazard_type(self):
        if not getattr(self, '_hazard_type', None):
            raise ValueError("Cannot use hazard-type-less {} here".format(self.__class__.__name__))
        return self._hazard_type


class AnalysisTypeAware(object):

    def set_analysis_type(self, ht):
        self._analysis_type = ht
        return self

    def get_analysis_type(self):
        if not getattr(self, '_analysis_type', None):
            raise ValueError("Cannot use analysis-type-less {} here".format(self.__class__.__name__))
        return self._analysis_type


class RiskAnalysisAware(object):
    def set_risk_analysis(self, ht):
        self._risk_analysis = ht
        return self

    def get_risk_analysis(self):
        if not getattr(self, '_risk_analysis', None):
            raise ValueError("Cannot use analysis-type-less {} here".format(self.__class__.__name__))
        return self._risk_analysis


class AnalysisType(HazardTypeAware, LocationAware, Exportable, models.Model):
    """
    For Risk Data Extraction it can be, as an instance, 'Loss Impact', 'Impact
    Analysis'. This object should also refer to any additional description
    and/or related resource useful to the users to get details on the
    Analysis type.
    """
    EXPORT_FIELDS = (('name', 'name',),
                     ('title', 'title',),
                     ('href', 'href',),)
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30, null=False, blank=False,
                            db_index=True)
    title = models.CharField(max_length=80, null=False, blank=False)
    description = models.TextField(default='', null=True, blank=False)

    def __unicode__(self):
        return u"{0}".format(self.name)

    class Meta:
        """
        """
        ordering = ['name']
        db_table = 'risks_analysistype'

    def href(self):
        loc = self.get_location()
        ht = self.get_hazard_type()
        return reverse('risks:analysis_type', args=(loc.code, ht.mnemonic, self.name,))

    def get_risk_analysis_list(self, **kwargs):
        loc = self.get_location()
        ht = self.get_hazard_type().set_location(loc)
        ra = self.riskanalysis_analysistype.filter(hazard_type=ht,
                                                   administrative_divisions__in=[loc])
        if kwargs:
            ra = ra.filter(**kwargs)
        risk_analysis = [r.set_location(loc)
                          .set_hazard_type(ht)
                          .set_analysis_type(self)
                         for r in ra.distinct()]
        return risk_analysis

    def get_analysis_details(self):
        risk_analysis = self.get_risk_analysis_list()
        out = self.export()
        out['riskAnalysis'] = [ra.export() for ra in risk_analysis]
        return out


class HazardType(LocationAware, Exportable, models.Model):
    """
    Describes an Hazard related to an Analysis and a Risk and pointing to
    additional resources on GeoNode.
    e.g.: Earthquake, Flood, Landslide, ...
    """

    EXPORT_FIELDS = (('mnemonic', 'mnemonic',),
                     ('title', 'title',),
                     ('riskAnalysis', 'risk_analysis_count',),
                     ('defaultAnalysisType', 'default_analysis_type',),
                     ('href', 'href',))

    id = models.AutoField(primary_key=True)
    mnemonic = models.CharField(max_length=30, null=False, blank=False,
                                db_index=True)
    title = models.CharField(max_length=80, null=False, blank=False)
    order = models.IntegerField()
    description = models.TextField(default='')
    gn_description = models.TextField('GeoNode description', default='',
                                      null=True)
    fa_class = models.CharField(max_length=64, default='fa-times')

    def __unicode__(self):
        return u"{0}".format(self.mnemonic)

    class Meta:
        """
        """
        ordering = ['order', 'mnemonic']
        db_table = 'risks_hazardtype'
        verbose_name_plural = 'Hazards'

    @property
    def risk_analysis_count(self):
        loc = self.get_location()
        ra = RiskAnalysis.objects.filter(administrative_divisions=loc,
                                         hazard_type=self)
        return ra.count()

    def get_analysis_types(self):
        loc = self.get_location()
        ra = RiskAnalysis.objects.filter(administrative_divisions=loc,
                                         hazard_type=self)

        at = AnalysisType.objects.filter(riskanalysis_analysistype__in=ra).distinct()
        return at

    def default_analysis_type(self):
        loc = self.get_location()
        at = self.get_analysis_types()
        if at.exists():
            at = at.first()
            return {'href': reverse('risks:analysis_type', args=(loc.code, self.mnemonic, at.name,))}
        else:
            return {}

    @property
    def href(self):
        loc = self.get_location()
        return reverse('risks:hazard_type', args=(loc.code, self.mnemonic,))

    def get_hazard_details(self):
        """
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


        """
        analysis_types = self.get_analysis_types()
        loc = self.get_location()
        out = {'mnemonic': self.mnemonic,
               'description': self.description,
               'analysisTypes': [at.set_location(loc).set_hazard_type(self).export() for at in analysis_types]}
        return out


class RiskAnalysis(LocationAware, HazardTypeAware, AnalysisTypeAware, Exportable, models.Model):
    """
    A type of Analysis associated to an Hazard (Earthquake, Flood, ...) and
    an Administrative Division.

    It defines a set of Dymensions (here we have the descriptors), to be used
    to filter SQLViews values on GeoServer.
    """

    EXPORT_FIELDS = (('name', 'name',),
                     ('hazardSet', 'get_hazard_set',),
                     ('href', 'href',),)
    EXPORT_FIELDS_EXTENDED = (('name', 'name',),
                              ('descriptorFile', 'descriptor_file',),
                              ('dataFile', 'data_file',),
                              ('metadataFile',  'metadata_file',),
                              ('hazardSet', 'get_hazard_set_extended',))

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30, null=False, blank=False,
                            db_index=True)

    descriptor_file = models.FileField(upload_to='descriptor_files', max_length=255)
    data_file = models.FileField(upload_to='metadata_files', max_length=255)
    metadata_file = models.FileField(upload_to='metadata_files', max_length=255)

    # Relationships
    analysis_type = models.ForeignKey(
        AnalysisType,
        related_name='riskanalysis_analysistype',
        on_delete=models.CASCADE,
        blank=False,
        null=False
    )

    hazard_type = models.ForeignKey(
        HazardType,
        related_name='riskanalysis_hazardtype',
        on_delete=models.CASCADE,
        blank=False,
        null=False
    )

    hazardset = models.ForeignKey(
        'HazardSet',
        related_name='hazardset',
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    administrative_divisions = models.ManyToManyField(
        "AdministrativeDivision",
        through='RiskAnalysisAdministrativeDivisionAssociation'
    )

    dymension_infos = models.ManyToManyField(
        "DymensionInfo",
        through='RiskAnalysisDymensionInfoAssociation'
    )

    def __unicode__(self):
        return u"{0}".format(self.name)

    class Meta:
        """
        """
        ordering = ['name']
        db_table = 'risks_riskanalysis'
        verbose_name_plural = 'Risks Analysis'

    def get_risk_details(self, dimension=None):
        """
        Returns dictionary with selected fields for
        """
        out = self.export(self.EXPORT_FIELDS_EXTENDED)
        return out

    def get_hazard_set_extended(self):
        return self.get_hazard_set(HazardSet.EXPORT_FIELDS_EXTENDED)

    def get_hazard_set(self, fields=None):
        if self.hazardset:
            return self.hazardset.export(fields)

    def href(self):
        loc = self.get_location()
        ht = self.get_hazard_type()
        at = self.get_analysis_type()
        return reverse('risks:data_extraction', args=(loc.code, ht.mnemonic, at.name, self.id,))


class AdministrativeDivisionManager(models.Manager):
    """
    """
    def get_by_natural_key(self, code):
        return self.get(code=code)


class AdministrativeDivision(Exportable, MPTTModel):
    """
    Administrative Division Gaul dataset.
    """

    EXPORT_FIELDS = (('label', 'name',),
                     ('href', 'href',),
                     ('geom', 'geom_href',),
                     ('parent_geom', 'parent_geom_href',),
                     )
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=30, null=False, unique=True,
                            db_index=True)
    name = models.CharField(max_length=30, null=False, blank=False,
                            db_index=True)
    # GeoDjango-specific: a geometry field (MultiPolygonField)
    # geom = gismodels.MultiPolygonField() - does not work w/ default db
    geom = models.TextField()  # As WKT
    srid = models.IntegerField(default=4326)

    # Relationships
    parent = TreeForeignKey('self', null=True, blank=True,
                            related_name='children')
    region = models.ForeignKey('Region')

    risks_analysis = models.ManyToManyField(
        RiskAnalysis,
        through='RiskAnalysisAdministrativeDivisionAssociation'
    )

    @property
    def href(self):
        return reverse('risks:location', args=(self.code,))

    @property
    def geom_href(self):
        return reverse('risks-geom:location', args=(self.code,))

    @property
    def parent_geom_href(self):
        if self.parent:
            return self.parent.geom_href;

    def __unicode__(self):
        return u"{0}".format(self.name)

    class Meta:
        """
        """
        ordering = ['code', 'name']
        db_table = 'risks_administrativedivision'
        verbose_name_plural = 'Administrative Divisions'

    class MPTTMeta:
        """
        """
        order_insertion_by = ['name']

    def get_parents_chain(self):
        parent = self.parent
        out = []
        while parent is not None:
            out.append(parent)
            parent = parent.parent
        out.reverse()
        return out


class Region(models.Model):
    """
    Groups a set of AdministrativeDivisions
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30, null=False, blank=False,
                            db_index=True)
    # level:
    # 0 is global
    # 1 is continent
    # 2 is sub-continent
    # 3 is country
    level = models.IntegerField(null=False, blank=False, db_index=True)

    # Relationships
    administrative_divisions = models.ManyToManyField(
        AdministrativeDivision,
        related_name='administrative_divisions'
    )

    def __unicode__(self):
        return u"{0}".format(self.name)

    class Meta:
        ordering = ['name', 'level']
        db_table = 'risks_region'
        verbose_name_plural = 'Regions'


class DymensionInfo(RiskAnalysisAware, Exportable, models.Model):
    """
    Set of Dymensions (here we have the descriptors), to be used
    to filter SQLViews values on GeoServer.

    The multi-dimensional vectorial layer in GeoServer will be something
    like this:

       {riskanalysis, dim1, dim2, ..., dimN, value}

    A set of DymensionInfo is something like:

     {name:'Round Period', value: 'RP-10', order: 0, unit: 'Years',
      attribute_name: 'dim1'}

     {name:'Round Period', value: 'RP-20', order: 1, unit: 'Years',
      attribute_name: 'dim1'}

     {name:'Round Period', value: 'RP-50', order: 2, unit: 'Years',
      attribute_name: 'dim1'}

     {name:'Scenario', value: 'Base', order: 0, unit: 'NA',
      attribute_name: 'dim2'}

     {name:'Scenario', value: 'Scenario-1', order: 1, unit: 'NA',
      attribute_name: 'dim2'}

     {name:'Scenario', value: 'Scenraio-2', order: 2, unit: 'NA',
      attribute_name: 'dim2'}

    Values on GeoServer SQL View will be filtered like:

     {riskanalysis: risk.identifier, dim1: 'RP-10', dim2: 'Base'} -> [values]

    """
    EXPORT_FIELDS = (('name', 'name',),
                     ('abstract', 'abstract',),
                     ('unit', 'unit',),
                     ('values', 'get_axis_values',),)

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30, null=False, blank=False,
                            db_index=True)
    abstract = models.TextField()
    unit = models.CharField(max_length=30)

    # Relationships
    risks_analysis = models.ManyToManyField(
        RiskAnalysis,
        through='RiskAnalysisDymensionInfoAssociation'
    )

    def __unicode__(self):
        return u"{0}".format(self.name)

    class Meta:
        """
        """
        ordering = ['name']
        db_table = 'risks_dymensioninfo'

    def get_axis_values(self):
        risk = self.get_risk_analysis()
        return list(self.riskanalysis_associacion.filter(riskanalysis=risk).values_list('value', flat=True))


class RiskAnalysisAdministrativeDivisionAssociation(models.Model):
    """
    Join table between RiskAnalysis and AdministrativeDivision
    """
    id = models.AutoField(primary_key=True)

    # Relationships
    riskanalysis = models.ForeignKey(RiskAnalysis)
    administrativedivision = models.ForeignKey(AdministrativeDivision)

    def __unicode__(self):
        return u"{0}".format(self.riskanalysis.name + " - " +
                             self.administrativedivision.name)

    class Meta:
        """
        """
        db_table = 'risks_riskanalysisadministrativedivisionassociation'


class RiskAnalysisDymensionInfoAssociation(models.Model):
    """
    Join table between RiskAnalysis and DymensionInfo
    """
    id = models.AutoField(primary_key=True)
    order = models.IntegerField()
    value = models.CharField(max_length=80, null=False, blank=False,
                             db_index=True)
    axis = models.CharField(max_length=10, null=False, blank=False,
                            db_index=True)

    # Relationships
    riskanalysis = models.ForeignKey(RiskAnalysis, related_name='dymensioninfo_associacion')
    dymensioninfo = models.ForeignKey(DymensionInfo, related_name='riskanalysis_associacion')

    DIM = {'x': 'dim1', 'y': 'dim2', 'z': 'dim3'}

    # GeoServer Layer referenced by GeoNode resource
    layer = models.ForeignKey(
        Layer,
        blank=False,
        null=False,
        unique=False,
        related_name='base_layer'
    )

    layer_attribute = models.CharField(max_length=80, null=False, blank=False)

    def __unicode__(self):
        return u"{0}".format(self.riskanalysis.name + " - " +
                             self.dymensioninfo.name)

    class Meta:
        """
        """
        ordering = ['order', 'value']
        db_table = 'risks_riskanalysisdymensioninfoassociation'

    def axis_to_dim(self):
        return self.DIM[self.axis]


class PointOfContact(Exportable, models.Model):
    """
    Risk Dataset Point of Contact; can be the poc or the author.
    """
    EXPORT_FILEDS = (('individualName', 'individual_name',),
                     ('organizationName', 'organization_name',),
                     ('positionName', 'position_name',),
                     ('deliveryPoint', 'delivery_point',),
                     ('city', 'city',),
                     ('postalCode', 'postal_code',),
                     ('email', 'e_mail',),
                     ('role', 'role',),)

    id = models.AutoField(primary_key=True)
    individual_name = models.CharField(max_length=255, null=False, blank=False)
    organization_name = models.CharField(max_length=255, null=False,
                                         blank=False)
    position_name = models.CharField(max_length=255)
    voice = models.CharField(max_length=255)
    facsimile = models.CharField(max_length=30)
    delivery_point = models.CharField(max_length=255)
    city = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=30)
    e_mail = models.CharField(max_length=255)
    role = models.CharField(max_length=255, null=False, blank=False)
    update_frequency = models.TextField()

    # Relationships
    administrative_area = models.ForeignKey(
        AdministrativeDivision,
        null=True,
        blank=True
    )

    country = models.ForeignKey(
        Region,
        null=True,
        blank=True
    )

    def __unicode__(self):
        return u"{0}".format(self.individual_name + " - " +
                             self.organization_name)

    class Meta:
        """
        """
        db_table = 'risks_pointofcontact'


class HazardSet(Exportable, models.Model):
    """
    Risk Dataset Metadata.

    Assuming the following metadata model:

    Section 1: Identification
     Title  	                     [M]
     Date  	                         [M]
     Date Type                       [M]
     Edition  	                     [O]
     Abstract  	                     [M]
     Purpose  	                     [O]
    Section 2: Point of Contact
     Individual Name  	             [M]
     Organization Name               [M]
     Position Name  	             [O]
     Voice  	                     [O]
     Facsimile  	                 [O]
     Delivery Point  	             [O]
     City  	                         [O]
     Administrative Area             [O]
     Postal Code  	                 [O]
     Country  	                     [O]
     Electronic Mail Address  	     [O]
     Role  	                         [M]
     Maintenance & Update Frequency  [O]
    Section 3: Descriptive Keywords
     Keyword  	                     [O]
     Country & Regions  	         [M]
     Use constraints  	             [M]
     Other constraints  	         [O]
     Spatial Representation Type  	 [O]
    Section 4: Equivalent Scale
     Language  	                     [M]
     Topic Category Code  	         [M]
    Section 5: Temporal Extent
     Begin Date  	                 [O]
     End Date  	                     [O]
     Geographic Bounding Box  	     [M]
     Supplemental Information  	     [M]
    Section 6: Distribution Info
     Online Resource  	             [O]
     URL  	                         [O]
     Description  	                 [O]
    Section 7: Reference System Info
     Code  	                         [O]
    Section8: Data quality info
     Statement	                     [O]
    Section 9: Metadata Author
     Individual Name  	             [M]
     Organization Name  	         [M]
     Position Name  	             [O]
     Voice  	                     [O]
     Facsimile  	                 [O]
     Delivery Point  	             [O]
     City  	                         [O]
     Administrative Area  	         [O]
     Postal Code  	                 [O]
     Country  	                     [O]
     Electronic Mail Address  	     [O]
     Role  	                         [O]
    """
    EXPORT_FIELDS = (('title', 'title',),
                     ('abstract', 'abstract',),
                     ('category', 'get_category',),
                     ('fa_icon', 'get_fa_icon'),)

    EXPORT_FIELDS_EXTENDED = (('title', 'title',),
                              ('date', 'date',),
                              ('dateType', 'date_type',),
                              ('edition', 'edition',),
                              ('abstract', 'abstract',),
                              ('purpose', 'purpose',),
                              ('keyword', 'keyword',),
                              ('useConstraints', 'use_contraints',),
                              ('otherConstraints', 'other_constraints',),
                              ('spatialRepresentationType', 'spatial_representation_type',),
                              ('language', 'language',),
                              ('beginDate', 'begin_date',),
                              ('endDate', 'end_date',),
                              ('bounds', 'bounds',),
                              ('supplementalInformation', 'supplemental_information',),
                              ('onlineResource', 'online_resource',),
                              ('url', 'url',),
                              ('description', 'description',),
                              ('referenceSystemCode', 'reference_system_code',),
                              ('dataQualityStatement', 'data_quality_statement',),
                              ('pointOfContact', 'get_poc',),
                              ('author', 'get_author',),
                              ('category', 'get_category',),
                              ('country', 'get_country',),)

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, null=False, blank=False)
    date = models.CharField(max_length=20, null=False, blank=False)
    date_type = models.CharField(max_length=20, null=False, blank=False)
    edition = models.CharField(max_length=30)
    abstract = models.TextField(null=False, blank=False)
    purpose = models.TextField()
    keyword = models.TextField()
    use_contraints = models.CharField(max_length=255, null=False, blank=False)
    other_constraints = models.CharField(max_length=255)
    spatial_representation_type = models.CharField(max_length=150)
    language = models.CharField(max_length=80, null=False, blank=False)
    begin_date = models.CharField(max_length=20)
    end_date = models.CharField(max_length=20)
    bounds = models.CharField(max_length=150, null=False, blank=False)
    supplemental_information = models.CharField(max_length=255, null=False,
                                                blank=False)
    online_resource = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    reference_system_code = models.CharField(max_length=30)
    data_quality_statement = models.TextField()

    # Relationships
    poc = models.ForeignKey(
        PointOfContact,
        related_name='point_of_contact'
    )

    author = models.ForeignKey(
        PointOfContact,
        related_name='metadata_author'
    )

    topic_category = models.ForeignKey(
        TopicCategory,
        blank=True,
        null=True,
        unique=False,
        related_name='category'
    )

    country = models.ForeignKey(
        Region,
        null=False,
        blank=False
    )

    riskanalysis = models.ForeignKey(
        RiskAnalysis,
        related_name='riskanalysis',
        blank=False,
        null=False
    )

    def __unicode__(self):
        return u"{0}".format(self.title)

    class Meta:
        """
        """
        db_table = 'risks_hazardset'

    def get_category(self):
        return self.topic_category.identifier

    def get_fa_icon(self):
        return self.topic_category.fa_class

    def get_poc(self):
        if self.poc:
            return self.poc.export()

    def get_author(self):
        if self.author:
            self.author.export()

    def get_country(self):
        if self.country:
            self.country.name


class FurtherResource(models.Model):
    """
    Additional GeoNode Resources which can be associated to:
    - A Region / Country
    - An Hazard
    - An Analysis Type
    - A Dymension Info
    - A Risk Analysis
    """
    id = models.AutoField(primary_key=True)
    text = models.TextField()

    # Relationships
    resource = models.ForeignKey(
        ResourceBase,
        blank=False,
        null=False,
        unique=False,
        related_name='resource')

    def __unicode__(self):
        return u"{0}".format(self.resource.title)

    class Meta:
        """
        """
        db_table = 'risks_further_resource'


class AnalysisTypeFurtherResourceAssociation(models.Model):
    """
    Layers, Documents and other GeoNode Resources associated to:
    - A Region / Country
    - An Hazard
    - An Analysis Type
    """
    id = models.AutoField(primary_key=True)

    # Relationships
    region = models.ForeignKey(
        Region,
        blank=True,
        null=True,
        unique=False,
    )

    hazard_type = models.ForeignKey(
        HazardType,
        blank=True,
        null=True,
        unique=False,
    )

    analysis_type = models.ForeignKey(
        AnalysisType,
        blank=True,
        null=True,
        unique=False,
    )

    resource = models.ForeignKey(
        FurtherResource,
        blank=False,
        null=False,
        unique=False,
        related_name='further_resource')

    def __unicode__(self):
        return u"{0}".format(self.resource)

    class Meta:
        db_table = 'risks_analysisfurtheresourceassociation'


class DymensionInfoFurtherResourceAssociation(models.Model):
    """
    Layers, Documents and other GeoNode Resources associated to:
    - A Region / Country
    - A Dymension Info
    - A Risk Analysis
    """
    id = models.AutoField(primary_key=True)

    # Relationships
    region = models.ForeignKey(
        Region,
        blank=True,
        null=True,
        unique=False,
    )

    riskanalysis = models.ForeignKey(
        RiskAnalysis,
        blank=True,
        null=True,
        unique=False,
    )

    dymension_info = models.ForeignKey(
        DymensionInfo,
        blank=True,
        null=True,
        unique=False,
    )

    resource = models.ForeignKey(
        FurtherResource,
        blank=False,
        null=False,
        unique=False,
        related_name='linked_resource')

    def __unicode__(self):
        return u"{0}".format(self.resource)

    class Meta:
        """
        """
        db_table = 'risks_dymensionfurtheresourceassociation'


class HazardSetFurtherResourceAssociation(models.Model):
    """
    Layers, Documents and other GeoNode Resources associated to:
    - A Region / Country
    - A Hazard Set
    """
    id = models.AutoField(primary_key=True)

    # Relationships
    region = models.ForeignKey(
        Region,
        blank=True,
        null=True,
        unique=False,
    )

    hazardset = models.ForeignKey(
        HazardSet,
        blank=True,
        null=True,
        unique=False,
    )

    resource = models.ForeignKey(
        FurtherResource,
        blank=False,
        null=False,
        unique=False,
        related_name='additional_resource')

    def __unicode__(self):
        return u"{0}".format(self.resource)

    class Meta:
        """
        """
        db_table = 'risks_hazardsetfurtheresourceassociation'


class RiskAnalysisCreate(models.Model):
    descriptor_file = models.FileField(upload_to='descriptor_files', max_length=255)

    def file_link(self):
        if self.descriptor_file:
            return "<a href='%s'>download</a>" % (self.descriptor_file.url,)
        else:
            return "No attachment"

    file_link.allow_tags = True

    def __unicode__(self):
        return u"{0}".format(self.descriptor_file.name)

    class Meta:
        ordering = ['descriptor_file']
        db_table = 'risks_descriptor_files'
        verbose_name = 'Risks Analysis: Create new through a .ini \
                        descriptor file'
        verbose_name_plural = 'Risks Analysis: Create new through a .ini \
                               descriptor file'


class RiskAnalysisImportData(models.Model):
    data_file = models.FileField(upload_to='data_files', max_length=255)

    # Relationships
    region = models.ForeignKey(
        Region,
        blank=False,
        null=False,
        unique=False,
    )

    riskanalysis = models.ForeignKey(
        RiskAnalysis,
        blank=False,
        null=False,
        unique=False,
    )

    def file_link(self):
        if self.data_file:
            return "<a href='%s'>download</a>" % (self.data_file.url,)
        else:
            return "No attachment"

    file_link.allow_tags = True

    def __unicode__(self):
        return u"{0}".format(self.data_file.name)

    class Meta:
        """
        """
        ordering = ['region', 'riskanalysis']
        db_table = 'risks_data_files'
        verbose_name = 'Risks Analysis: Import Risk Data from XLSX file'
        verbose_name_plural = 'Risks Analysis: Import Risk Data from XLSX file'


class RiskAnalysisImportMetadata(models.Model):
    """
    """
    metadata_file = models.FileField(upload_to='metadata_files', max_length=255)

    # Relationships
    region = models.ForeignKey(
        Region,
        blank=False,
        null=False,
        unique=False,
    )

    riskanalysis = models.ForeignKey(
        RiskAnalysis,
        blank=False,
        null=False,
        unique=False,
    )

    def file_link(self):
        if self.metadata_file:
            return "<a href='%s'>download</a>" % (self.metadata_file.url,)
        else:
            return "No attachment"

    file_link.allow_tags = True

    def __unicode__(self):
        return u"{0}".format(self.metadata_file.name)

    class Meta:
        """
        """
        ordering = ['region', 'riskanalysis']
        db_table = 'risks_metadata_files'
        verbose_name = 'Risks Analysis: Import or Update Risk Metadata from \
                        XLSX file'
        verbose_name_plural = 'Risks Analysis: Import or Update Risk Metadata \
                               from XLSX file'
