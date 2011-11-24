#!/usr/bin/env python
# encoding=utf-8

from scrapy.contrib.exporter import CsvItemExporter
from scrapy.contrib.exporter import JsonItemExporter
from scrapy.contrib.exporter import JsonLinesItemExporter
from scrapy.contrib.exporter import XmlItemExporter
from scrapy.contrib.exporter import BaseItemExporter

import json
import simplekml

class MTQInfraXmlItemExporter(XmlItemExporter):
    def serialize_field(self, field, name, value):
        # Base XML exporter expects strings only. Convert any float or int to string.
        if type(value) == float or type(value) == int:
            value = str(value)
        return super(MTQInfraXmlItemExporter, self).serialize_field(field, name, value)
        
class MTQInfraJsonItemExporter(JsonItemExporter):
    def __init__(self, file, **kwargs):
        # Base JSON exporter does not use dont_fail=True and I want to pass JSONEncoder args.
        self._configure(kwargs, dont_fail=True)
        self.file = file
        self.encoder = json.JSONEncoder(**kwargs)
        self.first_item = True

class MTQInfraKmlItemExporter(BaseItemExporter):
    def __init__(self, filename, **kwargs):
        self._configure(kwargs, dont_fail=True)
        self.filename = filename
        self.kml = simplekml.Kml()
        self.icon_styles = {}
        
    def _escape(self, str_value):
        # For now, we only deal with ampersand, the rest is properly escaped.
        return str_value.replace('&', '&amp;')
    
    def start_exporting(self):
        pass
    
    def export_item(self, item):
        if item['structure_name'] and item['structure_name'] != '-':
            name = "{:s} ({:s})".format(item['record_no'], self._escape(item['structure_name']))
        else:
            name = "{:s}".format(item['record_no'])
        # Appears under name in Google Earth
        snippet=simplekml.Snippet(content="{:s}, {:s}".format(self._escape(item['structure_type']),
                                                              self._escape(item['road'])),
                                  maxlines=1)
        # GCI code to text
        if item['gci'] == '4':
            gci_text = "Structure ne nécessitant aucune intervention"
        elif item['gci'] == '3':
            gci_text = "Structure nécessitant des réparations"
        elif item['gci'] == '2':
            gci_text = "Structure nécessitant des travaux majeurs"
        elif item['gci'] == '1':
            gci_text = "Structure nécessitant un remplacement"
        elif item['gci'] == 'AC':
            gci_text = "Analyse en cours"
        else:
            gci_text = "Sans objet"
        
        # Popup content
        description = """
            <table style="text-align:left;font-size:9pt;font-family:Helvetica;">
            <tbody>
            <tr><td colspan="2" style="text-align:center;font-size:10pt;"><img src="{:s}" alt="" style="height:200px; width:300px;"><br><b>{:s} ({:s})</b><br><br></td></tr>
            <tr><th>Indice de condition générale (ICG)</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Indice d'accessibilité (IAS)</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Année de construction</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Intervention planifiée</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Dernière inspection générale</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Prochaine inspection générale</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Route</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Type de route</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Nombre de voie</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Débit journalier moyen annuel (véhicules)</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>% camion</th><td style="text-align:center;">{:s}%</td></tr>
            <tr><th>Direction territoriale</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>MRC</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Municipalité</th><td style="text-align:center;">{:s}</td></tr>
            <tr><th>Fiche originale (MTQ)</th><td style="text-align:center;"><a href="{:s}">Fiche MTQ</a></td></tr>
            <tr><th>Localisation (MTQ)</th><td style="text-align:center;"><a href="{:s}"><img src="http://www.mtq.gouv.qc.ca/pls/apex/wwv_flow_file_mgr.get_file?p_security_group_id=1848625384920754&p_fname=Carte-01.gif" alt=""></a></td></tr>
            </tbody>
            </table>
        """.format(item['picture_href'], item['structure_type'], item['obstacle'], gci_text,
                      item['ai_desc'], item['construction_year'], item['planned_intervention'],
                      item['last_general_inspection_date'], item['next_general_inspection_date'],
                      item['road'], item['road_class'], item['num_lanes'], item['average_daily_flow_of_vehicles'],
                      item['percent_trucks'], item['territorial_direction'], item['rcm'], item['municipality'],
                      item['record_href'], item['location_href'])
        description = self._escape(description)
        
        # Add fields to KML entry.
        extendeddata = simplekml.ExtendedData()
        for field in self.fields_to_export:
            if field in ['latitude', 'longitude']:
                continue # Skip, already in KML data
            if type(field) == str:
                extendeddata.newdata(field, self._escape(item[field]), "")
            else:
                extendeddata.newdata(field, item[field], "")

        point = self.kml.newpoint(name=name,
                                  coords=[(item['longitude'], item['latitude'])],
                                  description=description,
                                  snippet=snippet,
                                  visibility=1,
                                  extendeddata=extendeddata,
                                 )
        
        # NOTE: Although my attempt here is to reuse the same style for multiple placemarks,
        #       simplekml does not appear to support this and create one style per placemark.
        iconstyle = self.icon_styles.get(item['ai_img_href'])
        if not iconstyle:
            iconstyle = simplekml.IconStyle()
            iconstyle.icon = simplekml.Icon(href=self._escape(item['ai_img_href']))
            self.icon_styles[item['ai_img_href']] = iconstyle
        point.iconstyle = iconstyle
        
    def finish_exporting(self):
        # NOTE: The KML file is over 40Mb in size. The XML serializing will take a while and will
        #       probably get your laptop fan to start :-)
        self.kml.save(self.filename)

