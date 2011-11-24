#!/usr/bin/env python
# encoding=utf-8

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.http import FormRequest
from scrapy.selector import HtmlXPathSelector
from scrapy import log
from mtqinfra.items import MTQInfraItem
import re

import sys
### Kludge to set default encoding to utf-8
reload(sys)
sys.setdefaultencoding('utf-8')

class MTQInfraSpider(BaseSpider):
    name = "mtqinfra"
    allowed_domains = ["www.mtq.gouv.qc.ca"]
    start_urls = [
        "http://www.mtq.gouv.qc.ca/pls/apex/f?p=102:56:::NO:RP::"
        # DEBUG: Use this url as a template to restart at a specific record number.
        #        Change session ID  (807952060873322) and pg_min_row (301) to proper values.
        #        NOTE: Also need to uncomment line in parse() method.
        #"http://www.mtq.gouv.qc.ca/pls/apex/f?p=102:56:807952060873322:pg_R_10432126941777590:NO&pg_min_row=301&pg_max_rows=15&pg_rows_fetched=15"
    ]

    def __init__(self, name=None, **kwargs):
        super(MTQInfraSpider, self).__init__(name, **kwargs)
        # Buffer to hold items during 2-steps scraping
        self.items_buffer = {}

    def parse(self, response):
        # DEBUG: Uncomment following line if restarting from specific record number.
        #return self.parse_main_list(response)
        # Submit empty form to obtain all data
        return [FormRequest.from_response(response,
                                          formdata={ "p_request": "RECHR" },
                                          callback=self.parse_main_list)]

    def parse_main_list(self, response):
        try:
            # Parse the main table
            hxs = HtmlXPathSelector(response)
            rows = hxs.select('//table[@id="R10432126941777590"]//table[@summary="Report"]/tr')
            if not rows:
                self.log("Failed to extract results table from response for URL '{:s}'. Has 'id' changed?".format(response.request.url), level=log.ERROR)
                return
            for row in rows:
                cells = row.select('td')
                # Skip header
                if not cells:
                    continue
                # Check if this is the last row. It contains only one cell and we must dig in to get page info
                if len(cells) == 1:
                    total_num_records = int(hxs.select('//table[@id="R19176911384131822"]/tr[2]/td/table/tr[8]/td[2]/text()').extract()[0])
                    first_record_on_page = int(cells[0].select('//span[@class="fielddata"]/text()').extract()[0].split('-')[0].strip())
                    last_record_on_page = int(cells[0].select('//span[@class="fielddata"]/text()').extract()[0].split('-')[1].strip())
                    self.log("Scraping details for records {:d} to {:d} of {:d} [{:.2f}% done].".format(first_record_on_page,
                                last_record_on_page, total_num_records, float(last_record_on_page)/float(total_num_records)*100), level=log.INFO)
                    # DEBUG: Switch check if you only want to process a certain number of records (e.g. 45)
                    #if last_record_on_page < 45:
                    if last_record_on_page < total_num_records:
                        page_links = cells[0].select('//a[@class="fielddata"]/@href').extract()
                        if len(page_links) == 1:
                            # On first page
                            next_page_href = page_links[0]
                        else:
                            next_page_href = page_links[1]
                        # Request to scrape next page
                        yield Request(url=response.request.url.split('?')[0]+'?'+next_page_href.split('?')[1], callback=self.parse_main_list)
                        continue
                    else:
                        # Nothing more to do
                        break

                # Cell 1: Record # + Record HREF
                record_no = cells[0].select('a/text()').extract()[0].strip()
                record_relative_href = cells[0].select('a/@href').extract()[0]
                record_href = response.request.url.split('?')[0]+'?'+record_relative_href.split('?')[1]
                structure_id = re.sub(ur"^.+:([0-9]+)$", ur'\1', record_href)
                # Cell 2: Name
                structure_name = "".join(cells[1].select('.//text()').extract()).strip()
                # Cell 3: Structure Type Image
                structure_type = cells[2].select('img/@alt').extract()[0]
                structure_type_img_relative_href = cells[2].select('img/@src').extract()[0]
                structure_type_img_href = re.sub(r'/[^/]*$', r'/', response.request.url) + structure_type_img_relative_href
                # Cell 4: Combined Territorial Direction + Municipality
                territorial_direction = "".join(cells[3].select('b//text()').extract()).strip()
                # NOTE: Municipality taken from details page as it was easier to parse.
                # Cell 5: Road
                road = "".join(cells[4].select('.//text()').extract()).strip()
                # Cell 6: Obstacle
                obstacle = "".join(cells[5].select('.//text()').extract()).strip()
                # Cell 7: GCI (General Condition Index)
                gci = cells[6].select('nobr/text()').extract()[0].strip()
                # Cell 8: AI (Accessibility Index)
                # Defaults to "no_restriction" as most records will have this code.
                ai_code = 'no_restriction'
                if cells[7].select('nobr/img/@alt'):
                    ai_desc = cells[7].select('nobr/img/@alt').extract()[0]
                    ai_img_relative_href = cells[7].select('nobr/img/@src').extract()[0]
                    ai_img_href = re.sub(r'/[^/]*$', r'/', response.request.url) + ai_img_relative_href
                else:
                    # If no image found for AI, then code = not available
                    ai_code = 'na'
                    if cells[7].select('nobr/text()'):
                        # Some text was available, use it
                        ai_desc = cells[7].select('nobr/text()').extract()[0]
                    else:
                        ai_desc = "N/D"
                    # Use our own Gray trafic light hosted on CloudApp
                    ai_img_href = "http://cl.ly/2r2A060b1g0N0l3f1y3L/feugris.png"
                # Set ai_code according to description if applicable
                if re.search(ur'certaines', ai_desc, re.I):
                    ai_code = 'restricted'
                elif re.search(ur'fermée', ai_desc, re.I):
                    ai_code = 'closed'
                # Cell 9: Location HREF
                onclick = cells[8].select('a/@onclick').extract()[0]
                location_href = re.sub(ur"^javascript:pop_url\('(.+)'\);$", ur'\1', onclick)
                # Cell 10: Planned Intervention
                planned_intervention = "".join(cells[9].select('.//text()').extract()).strip()
                # Cell 11: Report (yes/no image only) (SKIP)

                item = MTQInfraItem()
                item['record_no'] = record_no
                item['record_href'] = record_href
                item['structure_id'] = structure_id
                item['structure_name'] = structure_name
                item['structure_type'] = structure_type
                item['structure_type_img_href'] = structure_type_img_href
                item['territorial_direction'] = territorial_direction
                item['road'] = road
                item['obstacle'] = obstacle
                item['gci'] = gci
                item['ai_desc'] = ai_desc
                item['ai_img_href'] = ai_img_href
                item['ai_code'] = ai_code
                item['location_href'] = location_href
                item['planned_intervention'] = planned_intervention
                self.items_buffer[structure_id] = item
                # Request to scrape details
                yield Request(url=record_href, callback=self.parse_details)
        except Exception as e:
            # Something went wrong parsing this page. Log URL so we can determine which one.
            self.log("Parsing failed for URL '{:s}'".format(response.request.url), level=log.ERROR)
            raise # Re-raise exception

    def parse_details(self, response):
        # Parse the details of each structure
        try:
            # Extract structure ID from URL
            structure_id = response.request.url.split(':')[-1]
            hxs = HtmlXPathSelector(response)
            road_class = "".join(hxs.select('//table[@id="R3886317546232168"]/tr[2]/td/table[2]/tr[7]/td//text()').extract()).strip()
            municipality = "".join(hxs.select('//table[@id="R3886317546232168"]/tr[2]/td/table[2]/tr[9]/td//text()').extract()).strip()
            rcm = "".join(hxs.select('//table[@id="R3886317546232168"]/tr[2]/td/table[2]/tr[10]/td//text()').extract()).strip()
            latitude_text = hxs.select('//table[@id="R3886317546232168"]/tr[2]/td/table[3]/tr[2]/td[1]/text()').extract()[0].strip()
            latitude = float(latitude_text.replace(",", "."))
            longitude_text = hxs.select('//table[@id="R3886317546232168"]/tr[2]/td/table[3]/tr[2]/td[2]/text()').extract()[0].strip()
            longitude = float(longitude_text.replace(",", "."))
            construction_year = hxs.select('//table[@id="R3886317546232168"]/tr[2]/td/table[5]/tr[2]/td/text()').extract()[0].strip()
            # Picture is not always available
            picture_node = hxs.select('//img[@width="300px"][@height="200px"]/@src')
            if picture_node:
                picture_href = picture_node.extract()[0]
            else:
                picture_href = ""
            last_general_inspection_date = re.sub('\s+', ' ', "".join(hxs.select('//table[@id="R3885717878232165"]/tr[2]/td/table/tr[2]/td//text()').extract()).strip())
            next_general_inspection_date = re.sub('\s+', ' ', "".join(hxs.select('//table[@id="R3885717878232165"]/tr[2]/td/table/tr[3]/td//text()').extract()).strip())
            # The next fields can be missing if they do not apply
            average_daily_flow_of_vehicles_node = hxs.select('//table[@id="R3885913021232166"]/tr[2]/td/table[1]/tr[2]/td[1]/text()')
            if average_daily_flow_of_vehicles_node:
                # NOTE: Large number have spaces in them. Remove them.
                average_daily_flow_of_vehicles = average_daily_flow_of_vehicles_node.extract()[0].strip().replace(' ','')
            else:
                average_daily_flow_of_vehicles = "S.O."
            percent_trucks_node = hxs.select('//table[@id="R3885913021232166"]/tr[2]/td/table[1]/tr[2]/td[2]/text()')
            if percent_trucks_node:
                percent_trucks = percent_trucks_node.extract()[0].strip().replace('%','')
            else:
                percent_trucks = "S.O."
            num_lanes_node = hxs.select('//table[@id="R3885913021232166"]/tr[2]/td/table[2]/tr[2]/td/text()')
            if num_lanes_node:
                num_lanes = num_lanes_node.extract()[0].strip()
            else:
                num_lanes = "S.O."
        except Exception as e:
            # Something went wrong parsing this details page. Log structure ID so we can determine which one.
            self.log("Details parsing failed for structure '{:s}'".format(structure_id), level=log.ERROR)
            raise

        item = self.items_buffer[structure_id]
        item['road_class'] = road_class
        item['municipality'] = municipality
        item['rcm'] = rcm
        item['latitude'] = latitude
        item['longitude'] = longitude
        item['construction_year'] = construction_year
        item['picture_href'] = picture_href
        item['last_general_inspection_date'] = last_general_inspection_date
        item['next_general_inspection_date'] = next_general_inspection_date
        item['average_daily_flow_of_vehicles'] = average_daily_flow_of_vehicles
        item['percent_trucks'] = percent_trucks
        item['num_lanes'] = num_lanes

        del self.items_buffer[structure_id]
        return item

