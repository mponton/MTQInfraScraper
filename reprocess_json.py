#!/usr/bin/env python
# encoding=utf-8

import sys
### Kludge to set default encoding to utf-8
reload(sys)
sys.setdefaultencoding('utf-8')

from scrapy.contrib.exporter import CsvItemExporter
from scrapy.contrib.exporter import JsonItemExporter
from scrapy.contrib.exporter import JsonLinesItemExporter
from scrapy.contrib.exporter import XmlItemExporter
from scrapy.contrib.exporter import BaseItemExporter
import csv
import json
import simplekml
from mtqinfra.items import MTQInfraItem

#############################################################################
### NOTE: This is a quick and dirty example of a script to reprocess the
###       JSON data instead of rescraping if you need to change/add/remove
###       fields (assuming all you need is already in the JSON data).
#############################################################################

### I've copy-pasted the exporters here. You could modify them. If some of them
### do not change, just import the originals. This is only an example.

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

### I've copy-pasted the pipeline here and commented out the dispatcher.connect() calls
### in the constructor. Make any other modifications as needed.

class MTQInfraPipeline(object):
    def __init__(self):
        self.fields_to_export = [
            'latitude',
            'longitude',
            'record_no',
            'structure_id',
            'structure_name',
            'structure_type',
            'picture_href',
            'territorial_direction',
            'rcm',
            'municipality',
            'road',
            'road_class',
            'average_daily_flow_of_vehicles',
            'percent_trucks',
            'num_lanes',
            'obstacle',
            'gci',
            'ai_desc',
            'ai_img_href',
            'ai_code',
            'construction_year',
            'planned_intervention',
            'last_general_inspection_date',
            'next_general_inspection_date',
            'record_href',
            'location_href',
            'structure_type_img_href',
            'inspection_report_href',
            'limitation',
            'limitation_href'
        ]
        #dispatcher.connect(self.spider_opened, signals.spider_opened)
        #dispatcher.connect(self.spider_closed, signals.spider_closed)
        
    def spider_opened(self, spider):
        self.csv_exporter = CsvItemExporter(open(spider.name+".csv", "w"),
                                            fields_to_export=self.fields_to_export, quoting=csv.QUOTE_ALL)
        self.json_exporter = MTQInfraJsonItemExporter(open(spider.name+".json", "w"),
                                                      fields_to_export=self.fields_to_export,
                                                      sort_keys=True, indent=4)
        self.jsonlines_exporter = JsonLinesItemExporter(open(spider.name+".linejson", "w"),
                                                        fields_to_export=self.fields_to_export)

        self.xml_exporter = MTQInfraXmlItemExporter(open(spider.name+".xml", "w"),
                                                    fields_to_export=self.fields_to_export,
                                                    root_element="structures", item_element="structure")
        # Make a quick copy of the list
        kml_fields = self.fields_to_export[:]
        kml_fields.append('fusion_marker')
        self.kml_exporter = MTQInfraKmlItemExporter(spider.name+".kml", fields_to_export=kml_fields)
        self.csv_exporter.start_exporting()
        self.json_exporter.start_exporting()
        self.jsonlines_exporter.start_exporting()
        self.xml_exporter.start_exporting()
        self.kml_exporter.start_exporting()
        
    def process_item(self, item, spider):
        try:
            del item['fusion_marker']
        except:
            pass
        self.csv_exporter.export_item(item)
        self.json_exporter.export_item(item)
        self.jsonlines_exporter.export_item(item)
        self.xml_exporter.export_item(item)
        # Add fusion_marker to KML for use in Google Fusion Table
        if item['ai_code'] == "no_restriction":
            item['fusion_marker'] = "small_green"
        elif item['ai_code'] == "restricted":
            item['fusion_marker'] = "small_yellow"
        elif item['ai_code'] == "closed":
            item['fusion_marker'] = "small_red"
        else:
            item['fusion_marker'] = "small_blue"
        self.kml_exporter.export_item(item)
        return item
    
    def spider_closed(self, spider):
        self.csv_exporter.finish_exporting()
        self.json_exporter.finish_exporting()
        self.jsonlines_exporter.finish_exporting()
        self.xml_exporter.finish_exporting()
        self.kml_exporter.finish_exporting()

### Create a fake spider object with any fields/methods needed by your exporters.

class FakeSpider(object):
    # Set spider name
    # NOTE: Make sure you don't use the same one as the original spider because you'll
    #       overwrite the previous data (and with this implementation, script will fail too).
    name = "mtqinfra-reprocessed"
    
### MAIN

# This is the previously scraped data
input_file = open("mtqinfra.linejson")

pipeline = MTQInfraPipeline()
pipeline.spider_opened(FakeSpider)

for line in input_file:
    item = MTQInfraItem(json.loads(line))
    pipeline.process_item(item, FakeSpider)

pipeline.spider_closed(FakeSpider)
input_file.close()

