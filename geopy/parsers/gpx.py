from geopy import Point
from geopy.parsers.iso6709 import parse_iso6709

class VersionError(Exception):
    pass

class GPX(object):
    GPX_NS = "http://www.topografix.com/GPX/1/1"
    FILE_EXT = '.gpx'
    MIME_TYPE = 'application/gpx+xml'
    VERSION = '1.1'
    FIX_TYPES =  set(('none', '2d', '3d', 'dgps', 'pps'))
    DECIMAL_RE = re.compile(r'([+-]?\d*\.?\d+)$')
    GPX_TYPE = ({'version': 'string', 'creator': 'string'}, {
        'metadata': 'metadata', 'wpt': ['waypoint'], 'rte': ['route'],
        'trk': ['track'], 'extensions': 'extensions'
    })
    METADATA_TYPE = ({}, {
        'name': 'string', 'desc': 'string', 'author': 'person',
        'copyright': 'copyright', 'link': ['link'], 'time': 'datetime',
        'keywords': 'string', 'bounds': 'bounds', 'extensions': 'extensions'
    })
    WAYPOINT_TYPE = ({'lat': 'latitude', 'lon': 'longitude'}, {
        'ele': 'decimal', 'time': 'datetime', 'magvar': 'degrees',
        'geoidheight': 'decimal', 'name': 'string', 'cmt': 'string',
        'desc': 'string', 'src': 'string', 'link': ['link'], 'sym': 'string',
        'type': 'string', 'fix': 'fix', 'sat': 'unsigned', 'hdop': 'decimal',
        'vdop': 'decimal', 'pdop': 'decimal', 'ageofdgpsdata': 'decimal',
        'dgpsid': 'dgpsid', 'extensions': 'extensions'
    })
    ROUTE_TYPE = ({}, {
        'name': 'string', 'cmt': 'string', 'desc': 'string', 'src': 'string',
        'link': ['link'], 'number': 'unsigned', 'type': 'string',
        'extensions': 'extensions', 'rtept': ['waypoint']
    })
    TRACK_TYPE = ({}, {
        'name': 'string', 'cmt': 'string', 'desc': 'string', 'src': 'string',
        'link': ['link'], 'number': 'unsigned', 'type': 'string',
        'extensions': 'extensions', 'trkseg': ['segment']
    })
    TRACK_SEGMENT_TYPE = ({},
        {'trkpt': ['waypoint'], 'extensions': 'extensions'}
    )
    COPYRIGHT_TYPE = (
        {'author': 'string'}, {'year': 'year', 'license': 'uri'}
    )
    LINK_TYPE = ({'href': 'uri'}, {'text': 'string', 'type': 'string'})
    EMAIL_TYPE = ({'id': 'string', 'domain': 'string'}, {})
    PERSON_TYPE = ({}, {'name': 'string', 'email': 'email', 'link': 'link'})
    POINT_TYPE = ({'lat': 'longitude', 'lon': 'longitude'},
        {'ele': 'decimal', 'time': 'datetime'}
    )
    POINT_SEGMENT_TYPE = ({}, {'pt': ['point']})
    BOUNDS_TYPE = ({
        'minlat': 'latitude', 'minlon': 'longitude',
        'maxlat': 'latitude', 'maxlon': 'longitude'
    }, {})
    
    def __init__(self, document=None, cache=True):
        self.cache = cache
        self._waypoints = {}
        self._routes = {}
        self._tracks = {}
        self.type_handlers = {
            'string': lambda e: e.text,
            'uri': lambda e: e.text,
            'datetime': self._parse_datetime,
            'decimal': self._parse_decimal,
            'dgpsid': self._parse_dgps_station,
            'email': self._parse_email,
            'link': self._parse_link,
            'year': self._parse_int,
            'waypoint': self._parse_waypoint,
            'segment': self._parse_segment,
            'unsigned': self._parse_unsigned,
            'degrees': self._parse_degrees
        }
        
        if document is not None:
            if isinstance(document, basestring):
                document = ElementTree.fromstring(document)
            elif not ElementTree.iselement(document):
                document = ElementTree.parse(document)
            if document.tag == self._get_qname('gpx'):
                self._root = document
    
    @property
    def version(self):
        if not hasattr(self, '_version'):
            version = self._root.get('version')
            if version == self.VERSION:
                self._version = version
            else:
                raise VersionError("%r" % (version,))
        return self._version
    
    @property
    def creator(self):
        if not hasattr(self, '_creator'):
            self._creator = self._root.get('creator')
        return self._creator
    
    @property
    def metadata(self):
        if not hasattr(self, '_metadata'):
            metadata_qname = self._get_qname('metadata')
            metadata = {}
            element = self._root.find(metadata_qname)
            if element is not None:
                single, multi = self.METADATA
                metadata.update(self._child_dict(element, single, multi))
                for tag in ('name', 'desc', 'time', 'keywords'):
                    if tag in metadata:
                        metadata[tag] = metadata[tag]
                if 'time' in metadata:
                    metadata['time'] = self._parse_datetime(metadata['time'])
            self._metadata = metadata
        return self._metadata
    
    @property
    def waypoints(self):
        tag = self._get_qname('wpt')
        return self._cache_parsed(tag, self._parse_waypoint, self._waypoints)
    
    def _parse_waypoint(self, element):
        waypoint = {}
        point = Point(element.get('lat'), element.get('lon'))
    
    @property
    def routes(self):
        tag = self._get_qname('rte')
        return self._cache_parsed(tag, self._parse_route, self._routes)
    
    def _parse_route(self, element):
        pass
    
    @property
    def tracks(self):
        tag = self._get_qname('rte')
        return self._cache_parsed(tag, self._parse_track, self._tracks)
    
    def _parse_track(self, element):
        pass
    
    def _parse_type(self, element, type_def):
        attr_types, child_types = type_def
        attrs = {}
        children = {}
        for attr, handler in attr_types.iteritems():
            value = element.get(attr)
            type_func = self.type_handlers[handler]
            attrs[attr] = type_func(value)
        single = []
        multi = []
        for tag, handler in child_types.iteritems():
            if isinstance(handler, list):
                multi.append(tag)
            else:
                single.append(tag)
        elements = self._child_dict(element, single, multi)
    
    @property
    def extensions(self):
        extensions_qname = self._get_qname('extensions')
    
    def _cache_parsed(self, tag, parse_func, cache):
        i = -1
        for i in xrange(len(cache)):
            item = cache[i]
            if item is not None:
                yield item
        for element in self._root:
            if element.tag == tag:
                i += 1
                item = parse_func(element)
                if self.cache:
                    cache[i] = item
                if item is not None:
                    yield item
    
    def _parse_decimal(self, value):
        match = re.match(self.DECIMAL_RE, value)
        if match:
            return float(match.group(1))
        else:
            raise ValueError("Invalid decimal value: %r" % (value,))
    
    def _parse_degrees(self, value):
        value = self._parse_decimal(value)
        if 0 <= value <= 360:
            return value
        else:
            raise ValueError("Value out of range [0, 360]: %r" % (value,))
    
    def _parse_dgps_station(self, value):
        value = int(value)
        if 0 <= value <= 1023:
            return value
        else:
            raise ValueError("Value out of range [0, 1023]: %r" % (value,))
    
    def _parse_datetime(self, value):
        return parse_iso6709(value)
    
    def _parse_email(self, element):
        value = element.text
        if not value:
            name = element.get('id')
            domain = element.get('domain')
            if name and domain:
                return '@'.join((name, domain))
        return value or None
    
    def _parse_fix(self, value):
        if value in self.FIX_TYPES:
            return value
        else:
            raise ValueError("Value is not a valid fix type: %r" % (value,))
    
    def _parse_string(self, element):
        return element.text
    
    def _child_dict(self, element, single, multi):
        single = dict([(self._get_qname(tag), tag) for tag in single])
        multi = dict([(self._get_qname(tag), tag) for tag in multi])
        limit = len(single)
        d = {}
        if limit or multi:
            for child in element:
                if child.tag in single:
                    name = single.pop(child.tag)
                    d[name] = child
                    limit -= 1
                elif child.tag in multi:
                    name = multi[child.tag]
                    d.setdefault(name, []).append(child)
                if not limit and not multi:
                    break
        return d
    
    def _get_qname(self, name):
        return "{%s}%s" % (self.GPX_NS, name)
