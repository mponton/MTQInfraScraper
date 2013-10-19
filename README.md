## Overview

This is an experiment to scrape the Transports Quebec infrastructure [database](http://www.mtq.gouv.qc.ca/pls/apex/f?p=TBM:STRCT:::NO:RP,56::) and save the data in different, easily usable formats.

Please see [this blog post](http://blog.syslogd.net/2011/11/24/civic-hacking-with-python-part-2) for the technical details or [this blog post](http://blog.syslogd.net/2011/11/08/civic-hacking-with-python-part-1/) for the story and output files in CSV, JSON, LineJSON, XML and KML format.

## Requirements (Tested On)

* [Python](http://python.org) 2.7.x
* [Scrapy](http://scrapy.org) 0.13 and 0.14.4
* [simplekml](http://code.google.com/p/simplekml/) 0.8

Not tested with newer versions of the above. YMMV.

# NOTE

I currently have not plan to "support" this project. However, if you find and fix issues (e.g. stuff that does not work anymore because the HTML being scraped has been changed) or add features, feel free to send me pull requests.

If you find an issue that yourself have no plan to fix, feel free to open a ticket to let me know. Maybe by that time I will have found a portal to another dimension where I have extra time or a clone that would allow me to work on it.

Cheers!

# UPDATE 2013/10/18

Roberto Rocca [@robroc](https://twitter.com/robroc) from [The Gazette](http://blogs.montrealgazette.com/category/montreal/data-points/) [asked me](https://twitter.com/robroc/status/390918095499309056) if I had any recent scrape from the MTQ database.

I had not looked at this code in a long time and I was curious to see if it still worked. It did not.

However, by doing some tests in the Scrapy shell and checking HTML source code, I realized little would be necessary to fix things. So I found some time to update the scraper to have it work on the current MTQ website. Mostly, I had to change the base URL, the table IDs and XPath selector to get the structure photo URL.

**NOTE**: I did not test the code with the latest and greatest Scrapy version. Instead, to save myself trouble, I went with one of the oldest available version on PyPI (0.14.4) which did not require any change in my code.

**NOTE 2**: The latest version of the MTQ website uses cookies to track session. To easily break and inspect past the initial form submission, use [`inspect_response`](http://doc.scrapy.org/en/0.14/topics/shell.html#topics-shell-inspect-response) in `parse_main_list` or `parse_details`.

