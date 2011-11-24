#!/usr/bin/env python
# encoding=utf-8

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DropItem
from scrapy.contrib.exporter import CsvItemExporter
from scrapy.contrib.exporter import JsonLinesItemExporter
# Custom exporters
from exporters import MTQInfraJsonItemExporter
from exporters import MTQInfraXmlItemExporter
from exporters import MTQInfraKmlItemExporter
import csv


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
            'structure_type_img_href'
        ]
        dispatcher.connect(self.spider_opened, signals.spider_opened)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        
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
