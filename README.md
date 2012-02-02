## Overview

This is an experiment to scrape the Transports Quebec infrastructure [database](http://http://www.mtq.gouv.qc.ca/pls/apex/f?p=102:56:::NO:RP::) and save the data in different, easily usable formats.

Please see [this blog post](http://blog.syslogd.net/2011/11/24/civic-hacking-with-python-part-2) for the technical details or [this blog post](http://blog.syslogd.net/2011/11/08/civic-hacking-with-python-part-1/) for the story and output files in CSV, JSON, LineJSON, XML and KML format.

## Requirements (Tested On)

* [Python](http://python.org) 2.7.x
* [Scrapy](http://scrapy.org) 0.13
* [simplekml](http://code.google.com/p/simplekml/) 0.8

Not tested with newer versions of the above. YMMV.

# NOTE

I currently have not plan to "support" this project. However, if you find and fix issues (e.g. stuff that does not work anymore because the HTML being scraped has been changed) or add features, feel free to send me pull requests.

If you find an issue that yourself have no plan to fix, feel free to open a ticket to let me know. Maybe by that time I will have found a portal to another dimension where I have extra time or a clone that would allow me to work on it.

Cheers!