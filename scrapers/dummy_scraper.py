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
from salts_lib.utils import VIDEO_TYPES

from salts_lib.db_utils import DB_Connection

db_connection = DB_Connection()

class Dummy_Scraper(scraper.Scraper):
    def __init__(self):
        pass
    
    @classmethod
    def provides(cls):
        return [VIDEO_TYPES.TVSHOW, VIDEO_TYPES.SEASON, VIDEO_TYPES.EPISODE, VIDEO_TYPES.MOVIES]
    
    def get_name(self):
        return 'Dummy'
    
    def resolve_link(self, link):
        return link

    def format_source_label(self, item):
        pass
    
    def get_sources(self, video_type, title, year, season='', episode=''):
        return []

    def get_url(self, video_type, title, year, season='', episode=''):
        result=db_connection.get_related_url(video_type, title, year, self.get_name(), season, episode)
        if result:
            return result[0][0]

    def search(self, video_type, title, year):
        raise NotImplementedError
