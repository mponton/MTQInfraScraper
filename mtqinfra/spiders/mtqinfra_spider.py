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
        "http://www.mtq.gouv.qc.ca/pls/apex/f?p=TBM:STRCT:::NO:RP,56::"
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
            rows = hxs.select('//table[@id="R267337656202362799"]//table[@summary="Report"]/tr')
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
                    total_num_records = int(hxs.select('//table[@id="R262940246607215751"]/tr[2]/td/table/tr[6]/td[2]/text()').extract()[0])
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
                item['record_no'] = record_no                             # Fiche/Nº
                item['record_href'] = record_href                         # Fiche/Nº
                item['structure_id'] = structure_id                       # (determined from record_href)
                item['structure_name'] = structure_name                   # Nom
                item['structure_type'] = structure_type                   # Type
                item['structure_type_img_href'] = structure_type_img_href # Type
                item['territorial_direction'] = territorial_direction     # Direction territoriale
                item['road'] = road                                       # Route
                item['obstacle'] = obstacle                               # Obstacle
                item['gci'] = gci                                         # Indice de condition générale
                item['ai_desc'] = ai_desc                                 # Indice d'accessibilité
                item['ai_img_href'] = ai_img_href                         # Indice d'accessibilité
                item['ai_code'] = ai_code                                 # (determined from ai_desc)
                item['location_href'] = location_href                     # Diffusion des données spatiales
                item['planned_intervention'] = planned_intervention       # Intervention planifiée
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
            road_class = "".join(hxs.select('//table[@id="R260791846806817377"]/tr[2]/td/table[1]/tr[7]/td//text()').extract()).strip()
            municipality = "".join(hxs.select('//table[@id="R260791846806817377"]/tr[2]/td/table[1]/tr[9]/td//text()').extract()).strip()
            rcm = "".join(hxs.select('//table[@id="R260791846806817377"]/tr[2]/td/table[1]/tr[10]/td//text()').extract()).strip()
            latitude_text = hxs.select('//table[@id="R260791846806817377"]/tr[2]/td/table[2]/tr[2]/td[1]/text()').extract()[0].strip()
            latitude = float(latitude_text.replace(",", "."))
            longitude_text = hxs.select('//table[@id="R260791846806817377"]/tr[2]/td/table[2]/tr[2]/td[2]/text()').extract()[0].strip()
            longitude = float(longitude_text.replace(",", "."))
            construction_year = hxs.select('//table[@id="R260791846806817377"]/tr[2]/td/table[4]/tr[2]/td/text()').extract()[0].strip()
            # Picture is not always available
            picture_node = hxs.select("//img[contains(@src,'%s')]/@src" % structure_id)
            if picture_node:
                picture_href = picture_node.extract()[0]
            else:
                picture_href = ""
            last_general_inspection_date = re.sub('\s+', ' ', "".join(hxs.select('//table[@id="R260791247138817374"]/tr[2]/td/table/tr[2]/td//text()').extract()).strip())
            next_general_inspection_date = re.sub('\s+', ' ', "".join(hxs.select('//table[@id="R260791247138817374"]/tr[2]/td/table/tr[3]/td//text()').extract()).strip())
            # The next fields can be missing if they do not apply
            average_daily_flow_of_vehicles_node = hxs.select('//table[@id="R260791442281817375"]/tr[2]/td/table[1]/tr[2]/td[1]/text()')
            if average_daily_flow_of_vehicles_node:
                # NOTE: Large number have spaces in them. Remove them.
                average_daily_flow_of_vehicles = average_daily_flow_of_vehicles_node.extract()[0].strip().replace(' ','')
            else:
                average_daily_flow_of_vehicles = ""
            percent_trucks_node = hxs.select('//table[@id="R260791442281817375"]/tr[2]/td/table[1]/tr[2]/td[2]/text()')
            if percent_trucks_node:
                percent_trucks = percent_trucks_node.extract()[0].strip().replace('%','')
            else:
                percent_trucks = ""
            num_lanes_node = hxs.select('//table[@id="R260791442281817375"]/tr[2]/td/table[2]/tr[2]/td/text()')
            if num_lanes_node:
                num_lanes = num_lanes_node.extract()[0].strip()
            else:
                num_lanes = ""
            inspection_report_node = hxs.select('//table[@id="R268966050187887822"]/tr[2]/td/table[1]/tr[2]/td/a/@href')
            if inspection_report_node:
                inspection_report_href = 'http://www.mtq.gouv.qc.ca' + inspection_report_node.extract()[0]
            else:
                inspection_report_href = ""
            limitation_text_node = hxs.select('//table[@id="R297755049131147236"]/tr[2]/td/table[1]/tr[2]/td/a/text()')
            if limitation_text_node:
                limitation = limitation_text_node.extract()[0].strip()
            else:
                limitation = ""
            limitation_node = hxs.select('//table[@id="R297755049131147236"]/tr[2]/td/table[1]/tr[2]/td/a/@href')
            if limitation_node:
                limitation_href = 'http://www.mtq.gouv.qc.ca' + limitation_node.extract()[0]
            else:
                limitation_href = ""
        except Exception as e:
            # Something went wrong parsing this details page. Log structure ID so we can determine which one.
            self.log("Details parsing failed for structure '{:s}'".format(structure_id), level=log.ERROR)
            raise

        item = self.items_buffer[structure_id]
        item['road_class'] = road_class                                         # Route: Classe route
        item['municipality'] = municipality                                     # Municipalité
        item['rcm'] = rcm                                                       # MRC
        # @todo CEP
        # @todo Obstacle: Type de voie
        # @todo Obstacle: Classe route
        item['latitude'] = latitude                                             # Latitude
        item['longitude'] = longitude                                           # Longitude
        # @todo Longueur totale
        # @todo Longueur tablier
        # @todo Largeur hors tout
        # @todo Largeur carrossable
        # @todo Superficie tablier
        item['construction_year'] = construction_year                           # Année: Construction
        item['picture_href'] = picture_href
        item['last_general_inspection_date'] = last_general_inspection_date     # Dernière inspection générale
        item['next_general_inspection_date'] = next_general_inspection_date     # Prochaine inspection générale
        item['inspection_report_href'] = inspection_report_href                 # Rapport(s) d'inspection
        item['average_daily_flow_of_vehicles'] = average_daily_flow_of_vehicles # DJMA
        item['percent_trucks'] = percent_trucks                                 # % camion
        item['num_lanes'] = num_lanes                                           # Nombre de voies
        item['limitation'] = limitation                                         # Limitation
        item['limitation_href'] = limitation_href                               # Limitation

        del self.items_buffer[structure_id]
        return item

