# Scrapy settings for mtqinfra project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/topics/settings.html
#

BOT_NAME = 'mtqinfra'
BOT_VERSION = '1.0'

SPIDER_MODULES = ['mtqinfra.spiders']
NEWSPIDER_MODULE = 'mtqinfra.spiders'
USER_AGENT = '%s/%s' % (BOT_NAME, BOT_VERSION)

### Custom stuff

# Be gentle (and, anyway, the Oracle APEX site will return error pages if
# you attempt to use the same session ID in two or more concurrent sessions)
CONCURRENT_REQUESTS_PER_DOMAIN = 1
CONCURRENT_SPIDERS = 1

# Our do-it-all pipeline
ITEM_PIPELINES = [
    'mtqinfra.pipelines.MTQInfraPipeline'
]

# Log file. Comment if you want to send output to stdout (but I suggest
# you tail -f the file instead)
LOG_FILE = 'mtqinfra.log'
