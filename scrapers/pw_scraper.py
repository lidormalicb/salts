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
import re
import urllib2
import urllib
import urlparse
import xbmc
from salts_lib.db_utils import DB_Connection
from salts_lib import utils
from salts_lib.utils import VIDEO_TYPES

USER_AGENT = ("User-Agent:Mozilla/5.0 (Windows NT 6.2; WOW64)"
              "AppleWebKit/537.17 (KHTML, like Gecko)"
              "Chrome/24.0.1312.56")
db_connection = DB_Connection()

class PW_Scraper(scraper.Scraper):
    def __init__(self):
        self.base_url = 'http://www.primewire.ag'
    
    @classmethod
    def provides(cls):
        return [VIDEO_TYPES.TVSHOW, VIDEO_TYPES.SEASON, VIDEO_TYPES.EPISODE, VIDEO_TYPES.MOVIES]
    
    def get_name(self):
        return 'PrimeWire'
    
    def resolve_link(self, link):
        return link
    
    def format_source_label(self, item):
        label='[%s] %s (%s views)' % (item['quality'], item['host'], item['views'])
        if item['verified']: label = '[COLOR yellow]%s[/COLOR]' % (label)
        return label
    
    def get_sources(self, video_type, title, year, season='', episode=''):
        url = urlparse.urljoin(self.base_url, self.get_url(video_type, title, year, season, episode))
        html = self.__http_get(url, cache_limit=.5)
        adultregex = '<div class="offensive_material">.+<a href="(.+)">I understand'
        adult = re.search(adultregex, html, re.DOTALL)
        if adult:
            utils.log('Adult content url detected')
            adulturl = self.base_url + adult.group(1)
            headers = {'Referer': url}
            html = self.__get_url(adulturl, headers=headers, login=True)
        
        imdbregex = 'mlink_imdb">.+?href="http://www.imdb.com/title/(tt[0-9]{7}).*?"'
        match = re.search(imdbregex, html)
        if match:
            self.imdb_num = match.group(1)
        hosters = []
        container_pattern = r'<table[^>]+class="movie_version[ "][^>]*>(.*?)</table>'
        item_pattern = (
            r'quality_(?!sponsored|unknown)([^>]*)></span>.*?'
            r'url=([^&]+)&(?:amp;)?domain=([^&]+)&(?:amp;)?(.*?)'
            r'"version_veiws"> ([\d]+) views</')
        for container in re.finditer(container_pattern, html, re.DOTALL | re.IGNORECASE):
            for source in re.finditer(item_pattern, container.group(1), re.DOTALL):
                qual, url, host, parts, views = source.groups()
         
                item = {'host': host.decode('base-64'), 'url': url.decode('base-64')}
                item['verified'] = source.group(0).find('star.gif') > -1
                item['quality'] = qual.upper()
                item['views'] = int(views)
                pattern = r'<a href=".*?url=(.*?)&(?:amp;)?.*?".*?>(part \d*)</a>'
                other_parts = re.findall(pattern, parts, re.DOTALL | re.I)
                if other_parts:
                    item['multi-part'] = True
                    item['parts'] = [part[0].decode('base-64') for part in other_parts]
                else:
                    item['multi-part'] = False
                item['class']=self
                hosters.append(item)
     
        return hosters

    def get_url(self, video_type, title, year, season='', episode=''):
        temp_video_type=video_type
        if video_type == VIDEO_TYPES.EPISODE: temp_video_type=VIDEO_TYPES.TVSHOW
        url = None

        result = db_connection.get_related_url(temp_video_type, title, year, self.get_name())
        if result:
            url=result[0][0]
            utils.log('Got local related url: |%s|%s|%s|%s|%s|' % (temp_video_type, title, year, self.get_name(), url))
        else:
            results = self.search(temp_video_type, title, year)
            if results:
                url = results[0]['url']
                db_connection.set_related_url(temp_video_type, title, year, self.get_name(), url)

        if url and video_type==VIDEO_TYPES.EPISODE:
            result = db_connection.get_related_url(VIDEO_TYPES.EPISODE, title, year, self.get_name(), season, episode)
            if result:
                url=result[0][0]
                utils.log('Got local related url: |%s|%s|%s|%s|%s|%s|%s|' % (video_type, title, year, season, episode, self.get_name(), url))
            else:
                show_url = url
                url = self.__get_episode_url(show_url, season, episode)
                if url:
                    db_connection.set_related_url(VIDEO_TYPES.EPISODE, title, year, self.get_name(), url, season, episode)
        
        return url
    
    def search(self, video_type, title, year):
        search_url = urlparse.urljoin(self.base_url, '/index.php?search_keywords=')
        search_url += urllib.quote_plus(title)
        search_url += '&year=' + urllib.quote_plus(year)
        if video_type in [VIDEO_TYPES.TVSHOW, VIDEO_TYPES.EPISODE]:
            search_url += '&search_section=2'
        else:
            search_url += '&search_section=1'
            
        html = self. __http_get(self.base_url, cache_limit=0)
        r = re.search('input type="hidden" name="key" value="([0-9a-f]*)"', html).group(1)
        search_url += '&key=' + r
        
        html = self.__http_get(search_url, cache_limit=.25)
        pattern = r'class="index_item.+?href="(.+?)" title="Watch (.+?)"?\(?([0-9]{4})?\)?"?>'
        results=[]
        for match in re.finditer(pattern, html):
            result={}
            url, title, year = match.groups()
            result['url']=url
            result['title']=title
            result['year']=year
            results.append(result)
        return results
    
    def __get_episode_url(self, show_url, season, episode):
        url = urlparse.urljoin(self.base_url, show_url)
        html = self.__http_get(url, cache_limit=2)
        pattern = '"tv_episode_item".+?href="(.+?)">.*?</a>'
        episodes = re.finditer(pattern, html, re.DOTALL)
        for ep in episodes:
            ep_url = ep.group(1)
            match_season = re.search('/season-([0-9]{1,4})-', ep_url).group(1)
            match_episode = re.search('-episode-([0-9]{1,3})', ep_url).group(1)
            if match_season == season and match_episode == episode:
                return ep_url
        
    def __http_get(self, url, cache_limit=8):
        utils.log('Getting Url: %s' % (url))
        db_connection=DB_Connection()
        html = db_connection.get_cached_url(url, cache_limit)
        if html:
            utils.log('Returning cached result for: %s' % (url), xbmc.LOGDEBUG)
            return html
        
        request = urllib2.Request(url)
        request.add_header('User-Agent', USER_AGENT)
        request.add_unredirected_header('Host', request.get_host())
        request.add_unredirected_header('Referer', self.base_url)
        response = urllib2.urlopen(request, timeout=10)
        html=response.read()
        db_connection.cache_url(url, html)
        return html
        