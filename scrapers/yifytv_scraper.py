"""
    SALTS XBMC Addon
    Copyright (C) 2014 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import scraper
import urllib
import urlparse
import re
import json
import xbmcaddon
from salts_lib import log_utils
from salts_lib.constants import VIDEO_TYPES
from salts_lib.db_utils import DB_Connection
from salts_lib.constants import QUALITIES

BASE_URL = 'http://yify.tv'

class YIFY_Scraper(scraper.Scraper):
    base_url=BASE_URL
    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout=timeout
        self.db_connection = DB_Connection()
        self.base_url = xbmcaddon.Addon().getSetting('%s-base_url' % (self.get_name()))
    
    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.MOVIE])
    
    @classmethod
    def get_name(cls):
        return 'yify.tv'
    
    def resolve_link(self, link):
        url = urlparse.urljoin(self.base_url,link)
        html = self.__http_get(url, cache_limit=.5)
        data = json.loads(html)
        for elem in data:
            print elem
            if elem['type'].startswith('video'):
                url = elem['url']
        return url

    def format_source_label(self, item):
        return '[%s] %s (%s views) (%s/100)' % (item['quality'], item['host'],  item['views'], item['rating'])
    
    def get_sources(self, video_type, title, year, season='', episode=''):
        source_url= self.get_url(video_type, title, year, season, episode)
        hosters=[]
        if source_url:
            url = urlparse.urljoin(self.base_url,source_url)
            html = self.__http_get(url, cache_limit=.5)
            match = re.search('showPkPlayer\("([^"]+)', html)
            if match:
                video_id = match.group(1)
                url = '/reproductor2/pk/pk/plugins/player_p2.php?url=%s' % (video_id)
                hoster = {'multi-part': False, 'host': 'yify.tv', 'class': self, 'quality': QUALITIES.HD, 'views': None, 'rating': None, 'url': url}
                match = re.search('class="votes">(\d+)</strong>', html)
                if match:
                    hoster['views']=match.group(1)
                hosters.append(hoster)
        return hosters

    def get_url(self, video_type, title, year, season='', episode=''):
        url = None
        result = self.db_connection.get_related_url(video_type, title, year, self.get_name())
        if result:
            url=result[0][0]
            log_utils.log('Got local related url: |%s|%s|%s|%s|%s|' % (video_type, title, year, self.get_name(), url))
        else:
            results = self.search(video_type, title, year)
            if results:
                url = results[0]['url']
                self.db_connection.set_related_url(video_type, title, year, self.get_name(), url)
        return url

    def search(self, video_type, title, year):
        search_url = urlparse.urljoin(self.base_url, '/?no&order=desc&years=%s&s=' %  (year))
        search_url += urllib.quote_plus(title)
        html = self.__http_get(search_url, cache_limit=.25)
        results=[]
        pattern ='var\s+posts\s+=\s+(.*);'
        match = re.search(pattern, html)
        if match:
            fragment = match.group(1)
            data = json.loads(fragment)
            for post in data['posts']:
                result = {'title': post['title'], 'year': post['year'], 'url': post['link'].replace(self.base_url,'')}
                results.append(result)
        return results

    def __http_get(self, url, cache_limit=8):
        return super(YIFY_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, cache_limit=cache_limit)
