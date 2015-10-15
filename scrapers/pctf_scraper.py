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
from salts_lib import kodi
from salts_lib.constants import VIDEO_TYPES
from salts_lib.constants import FORCE_NO_MATCH
from salts_lib.constants import QUALITIES
from salts_lib.constants import USER_AGENT
from salts_lib import dom_parser

BASE_URL = 'https://popcorntimefree.info'

class PopcornTime_Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = kodi.get_setting('%s-base_url' % (self.get_name()))

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.MOVIE])

    @classmethod
    def get_name(cls):
        return 'popcorntimefree'

    def resolve_link(self, link):
        return link

    def format_source_label(self, item):
        return '[%s] %s' % (item['quality'], item['host'])

    def get_sources(self, video):
        source_url = self.get_url(video)
        hosters = []
        if source_url and source_url != FORCE_NO_MATCH:
            url = urlparse.urljoin(self.base_url, source_url)
            html = self._http_get(url, cache_limit=.5)
            match = re.search('<source[^>]*src="([^"]+)', html)
            if match:
                stream_url = match.group(1)
                host = self._get_direct_hostname(stream_url)
                _title, _year, height, _extra = self._parse_movie_link(stream_url)
                stream_url += '|User-Agent=%s' % (USER_AGENT)
                hoster = {'multi-part': False, 'url': stream_url, 'class': self, 'quality': self._height_get_quality(height), 'host': host, 'rating': None, 'views': None, 'direct': True}
                hosters.append(hoster)
        return hosters

    def get_url(self, video):
        return super(PopcornTime_Scraper, self)._default_get_url(video)

    def search(self, video_type, title, year):
        search_url = urlparse.urljoin(self.base_url, '/?s=')
        search_url += urllib.quote_plus(title)
        html = self._http_get(search_url, cache_limit=.25)
        results = []
        for item in dom_parser.parse_dom(html, 'h2', {'class': 'entry-title'}):
            match = re.search('href="([^"]+)[^>]+>([^<]+)', item)
            if match:
                url, match_title_year = match.groups()
                match = re.search('(.*?)\s+\(?(\d{4})\)?', match_title_year)
                if match:
                    match_title, match_year = match.groups()
                else:
                    match_title = match_title_year
                    match_year = ''
    
                if not year or not match_year or year == match_year:
                    result = {'title': match_title, 'year': match_year, 'url': url.replace(self.base_url, '')}
                    results.append(result)

        return results

    def __strip_link(self, html):
        text = dom_parser.parse_dom(html, 'a')
        if text:
            return text[0]
        else:
            return html
    
    def _http_get(self, url, data=None, cache_limit=8):
        return super(PopcornTime_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, data=data, cache_limit=cache_limit)
