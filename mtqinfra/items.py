# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class MTQInfraItem(Item):
    # From main table
    record_no = Field()
    record_href = Field()
    structure_id = Field()
    structure_name = Field()
    structure_type = Field()
    structure_type_img_href = Field()
    territorial_direction = Field()
    rcm = Field()
    municipality = Field()
    road = Field()
    obstacle = Field()
    gci = Field()
    ai_desc = Field()
    ai_img_href = Field()
    ai_code = Field()
    location_href = Field()
    planned_intervention = Field()
    # From details
    road_class = Field()
    latitude = Field()
    longitude = Field()
    construction_year = Field()
    picture_href = Field()
    last_general_inspection_date = Field()
    next_general_inspection_date = Field()
    inspection_report_href = Field()
    average_daily_flow_of_vehicles = Field()
    percent_trucks = Field()
    num_lanes = Field()
    limitation = Field()
    limitation_href = Field()
    fusion_marker = Field()
