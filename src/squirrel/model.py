# http://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------

'''
Data model and content types handled by the Squirrel framework.

Squirrel uses flat content types to represent waveform, station, channel,
response, event, and a few other objects. A common subset of the information in
these objects is indexed in the database, currently: kind, codes, time interval
and sampling rate. The :py:class:`Nut` objects encapsulate this information
together with information about where and how to get the associated bulk data.

Further content types are defined here to handle waveform orders, waveform
promises, data coverage and sensor information.
'''

from __future__ import absolute_import, print_function

import re
import fnmatch
import hashlib
import numpy as num
from os import urandom
from base64 import urlsafe_b64encode
from collections import defaultdict, namedtuple

from pyrocko import util
from pyrocko.guts import Object, SObject, String, Timestamp, Float, Int, \
    Unicode, Tuple, List, StringChoice, Any
from pyrocko.model import squirrel_content, Location
from pyrocko.response import FrequencyResponse, MultiplyResponse, \
    IntegrationResponse, DifferentiationResponse, simplify_responses, \
    FrequencyResponseCheckpoint

from .error import ConversionError, SquirrelError


guts_prefix = 'squirrel'


g_codes_pool = {}


class CodesError(SquirrelError):
    pass


class Codes(SObject):
    pass


def normalize_nslce(*args, **kwargs):
    if args and kwargs:
        raise ValueError('Either *args or **kwargs accepted, not both.')

    if len(args) == 1:
        if isinstance(args[0], str):
            args = tuple(args[0].split('.'))
        elif isinstance(args[0], tuple):
            args = args[0]
        else:
            raise ValueError('Invalid argument type: %s' % type(args[0]))

    nargs = len(args)
    if nargs == 5:
        t = args

    elif nargs == 4:
        t = args + ('',)

    elif nargs == 0:
        d = dict(
            network='',
            station='',
            location='',
            channel='',
            extra='')

        d.update(kwargs)
        t = tuple(kwargs.get(k, '') for k in (
            'network', 'station', 'location', 'channel', 'extra'))

    else:
        raise CodesError(
            'Does not match NSLC or NSLCE codes pattern: %s' % '.'.join(args))

    if '.'.join(t).count('.') != 4:
        raise CodesError(
            'Codes may not contain a ".": "%s", "%s", "%s", "%s", "%s"' % t)

    return t


CodesNSLCEBase = namedtuple(
    'CodesNSLCEBase', [
        'network', 'station', 'location', 'channel', 'extra'])


class CodesNSLCE(CodesNSLCEBase, Codes):
    '''
    Codes denominating a seismic channel (NSLC or NSLCE).

    FDSN/SEED style NET.STA.LOC.CHA is accepted or NET.STA.LOC.CHA.EXTRA, where
    the EXTRA part in the latter form can be used to identify a custom
    processing applied to a channel.
    '''

    __slots__ = ()
    __hash__ = CodesNSLCEBase.__hash__

    as_dict = CodesNSLCEBase._asdict

    def __new__(cls, *args, safe_str=None, **kwargs):
        nargs = len(args)
        if nargs == 1 and isinstance(args[0], CodesNSLCE):
            return args[0]
        elif nargs == 1 and isinstance(args[0], CodesNSL):
            t = (args[0].nsl) + ('*', '*')
        elif nargs == 1 and isinstance(args[0], CodesX):
            t = ('*', '*', '*', '*', '*')
        elif safe_str is not None:
            t = safe_str.split('.')
        else:
            t = normalize_nslce(*args, **kwargs)

        x = CodesNSLCEBase.__new__(cls, *t)
        return g_codes_pool.setdefault(x, x)

    def __init__(self, *args, **kwargs):
        Codes.__init__(self)

    def __str__(self):
        if self.extra == '':
            return '.'.join(self[:-1])
        else:
            return '.'.join(self)

    def __eq__(self, other):
        if not isinstance(other, CodesNSLCE):
            other = CodesNSLCE(other)

        return CodesNSLCEBase.__eq__(self, other)

    @property
    def safe_str(self):
        return '.'.join(self)

    @property
    def nslce(self):
        return self[:4]

    @property
    def nslc(self):
        return self[:4]

    @property
    def nsl(self):
        return self[:3]

    @property
    def ns(self):
        return self[:2]

    def as_tuple(self):
        return tuple(self)

    def replace(self, **kwargs):
        x = CodesNSLCEBase._replace(self, **kwargs)
        return g_codes_pool.setdefault(x, x)


def normalize_nsl(*args, **kwargs):
    if args and kwargs:
        raise ValueError('Either *args or **kwargs accepted, not both.')

    if len(args) == 1:
        if isinstance(args[0], str):
            args = tuple(args[0].split('.'))
        elif isinstance(args[0], tuple):
            args = args[0]
        else:
            raise ValueError('Invalid argument type: %s' % type(args[0]))

    nargs = len(args)
    if nargs == 3:
        t = args

    elif nargs == 0:
        d = dict(
            network='',
            station='',
            location='')

        d.update(kwargs)
        t = tuple(kwargs.get(k, '') for k in (
            'network', 'station', 'location'))

    else:
        raise CodesError(
            'Does not match NSL codes pattern: %s' % '.'.join(args))

    if '.'.join(t).count('.') != 2:
        raise CodesError(
            'Codes may not contain a ".": "%s", "%s", "%s"' % t)

    return t


CodesNSLBase = namedtuple(
    'CodesNSLBase', [
        'network', 'station', 'location'])


class CodesNSL(CodesNSLBase, Codes):
    '''
    Codes denominating a seismic station (NSL).

    NET.STA.LOC is accepted, slightly different from SEED/StationXML, where
    LOC is part of the channel. By setting location='*' is possible to get
    compatible behaviour in most cases.
    '''

    __slots__ = ()
    __hash__ = CodesNSLBase.__hash__

    as_dict = CodesNSLBase._asdict

    def __new__(cls, *args, safe_str=None, **kwargs):
        nargs = len(args)
        if nargs == 1 and isinstance(args[0], CodesNSL):
            return args[0]
        elif nargs == 1 and isinstance(args[0], CodesNSLCE):
            t = args[0].nsl
        elif nargs == 1 and isinstance(args[0], CodesX):
            t = ('*', '*', '*')
        elif safe_str is not None:
            t = safe_str.split('.')
        else:
            t = normalize_nsl(*args, **kwargs)

        x = CodesNSLBase.__new__(cls, *t)
        return g_codes_pool.setdefault(x, x)

    def __init__(self, *args, **kwargs):
        Codes.__init__(self)

    def __str__(self):
        return '.'.join(self)

    def __eq__(self, other):
        if not isinstance(other, CodesNSL):
            other = CodesNSL(other)

        return CodesNSLBase.__eq__(self, other)

    @property
    def safe_str(self):
        return '.'.join(self)

    @property
    def ns(self):
        return self[:2]

    @property
    def nsl(self):
        return self[:3]

    def as_tuple(self):
        return tuple(self)

    def replace(self, **kwargs):
        x = CodesNSLBase._replace(self, **kwargs)
        return g_codes_pool.setdefault(x, x)


CodesXBase = namedtuple(
    'CodesXBase', [
        'name'])


class CodesX(CodesXBase, Codes):
    '''
    General purpose codes for anything other than channels or stations.
    '''

    __slots__ = ()
    __hash__ = CodesXBase.__hash__
    __eq__ = CodesXBase.__eq__

    as_dict = CodesXBase._asdict

    def __new__(cls, name='', safe_str=None):
        if isinstance(name, CodesX):
            return name
        elif isinstance(name, (CodesNSLCE, CodesNSL)):
            name = '*'
        elif safe_str is not None:
            name = safe_str
        else:
            if '.' in name:
                raise CodesError('Code may not contain a ".": %s' % name)

        x = CodesXBase.__new__(cls, name)
        return g_codes_pool.setdefault(x, x)

    def __init__(self, *args, **kwargs):
        Codes.__init__(self)

    def __str__(self):
        return '.'.join(self)

    @property
    def safe_str(self):
        return '.'.join(self)

    @property
    def ns(self):
        return self[:2]

    def as_tuple(self):
        return tuple(self)

    def replace(self, **kwargs):
        x = CodesXBase._replace(self, **kwargs)
        return g_codes_pool.setdefault(x, x)


g_codes_patterns = {}


def match_codes(pattern, codes):
    spattern = pattern.safe_str
    scodes = codes.safe_str
    if spattern not in g_codes_patterns:
        rpattern = re.compile(fnmatch.translate(spattern), re.I)
        g_codes_patterns[spattern] = rpattern

    rpattern = g_codes_patterns[spattern]
    return bool(rpattern.match(scodes))


g_content_kinds = [
    'undefined',
    'waveform',
    'station',
    'channel',
    'response',
    'event',
    'waveform_promise']


g_codes_classes = [
    CodesX,
    CodesNSLCE,
    CodesNSL,
    CodesNSLCE,
    CodesNSLCE,
    CodesX,
    CodesNSLCE]

g_codes_classes_ndot = {
    0: CodesX,
    2: CodesNSL,
    3: CodesNSLCE,
    4: CodesNSLCE}


def to_codes_simple(kind_id, codes_safe_str):
    return g_codes_classes[kind_id](safe_str=codes_safe_str)


def to_codes(kind_id, obj):
    return g_codes_classes[kind_id](obj)


def to_codes_guess(s):
    try:
        return g_codes_classes_ndot[s.count('.')](s)
    except KeyError:
        raise CodesError('Cannot guess codes type: %s' % s)


g_content_kind_ids = (
    UNDEFINED, WAVEFORM, STATION, CHANNEL, RESPONSE, EVENT,
    WAVEFORM_PROMISE) = range(len(g_content_kinds))


g_tmin, g_tmax = util.get_working_system_time_range()[:2]


try:
    g_tmin_queries = max(g_tmin, util.str_to_time_fillup('1900-01-01'))
except Exception:
    g_tmin_queries = g_tmin


def to_kind(kind_id):
    return g_content_kinds[kind_id]


def to_kinds(kind_ids):
    return [g_content_kinds[kind_id] for kind_id in kind_ids]


def to_kind_id(kind):
    return g_content_kinds.index(kind)


def to_kind_ids(kinds):
    return [g_content_kinds.index(kind) for kind in kinds]


g_kind_mask_all = 0xff


def to_kind_mask(kinds):
    if kinds:
        return sum(1 << kind_id for kind_id in to_kind_ids(kinds))
    else:
        return g_kind_mask_all


def str_or_none(x):
    if x is None:
        return None
    else:
        return str(x)


def float_or_none(x):
    if x is None:
        return None
    else:
        return float(x)


def int_or_none(x):
    if x is None:
        return None
    else:
        return int(x)


def int_or_g_tmin(x):
    if x is None:
        return g_tmin
    else:
        return int(x)


def int_or_g_tmax(x):
    if x is None:
        return g_tmax
    else:
        return int(x)


def tmin_or_none(x):
    if x == g_tmin:
        return None
    else:
        return x


def tmax_or_none(x):
    if x == g_tmax:
        return None
    else:
        return x


def time_or_none_to_str(x):
    if x is None:
        return '...'.ljust(17)
    else:
        return util.time_to_str(x)


def codes_to_str_abbreviated(codes, indent='  '):
    codes = [str(x) for x in codes]

    if len(codes) > 20:
        scodes = '\n' + util.ewrap(codes[:10], indent=indent) \
            + '\n%s[%i more]\n' % (indent, len(codes) - 20) \
            + util.ewrap(codes[-10:], indent='  ')
    else:
        scodes = '\n' + util.ewrap(codes, indent=indent) \
            if codes else '<none>'

    return scodes


g_offset_time_unit_inv = 1000000000
g_offset_time_unit = 1.0 / g_offset_time_unit_inv


def tsplit(t):
    if t is None:
        return None, 0.0

    t = util.to_time_float(t)
    if type(t) is float:
        t = round(t, 5)
    else:
        t = round(t, 9)

    seconds = num.floor(t)
    offset = t - seconds
    return int(seconds), int(round(offset * g_offset_time_unit_inv))


def tjoin(seconds, offset):
    if seconds is None:
        return None

    return util.to_time_float(seconds) \
        + util.to_time_float(offset*g_offset_time_unit)


tscale_min = 1
tscale_max = 365 * 24 * 3600  # last edge is one above
tscale_logbase = 20

tscale_edges = [tscale_min]
while True:
    tscale_edges.append(tscale_edges[-1]*tscale_logbase)
    if tscale_edges[-1] >= tscale_max:
        break


tscale_edges = num.array(tscale_edges)


def tscale_to_kscale(tscale):

    # 0 <= x < tscale_edges[1]: 0
    # tscale_edges[1] <= x < tscale_edges[2]: 1
    # ...
    # tscale_edges[len(tscale_edges)-1] <= x: len(tscale_edges)

    return int(num.searchsorted(tscale_edges, tscale))


@squirrel_content
class Station(Location):
    '''
    A seismic station.
    '''

    codes = CodesNSL.T()

    tmin = Timestamp.T(optional=True)
    tmax = Timestamp.T(optional=True)

    description = Unicode.T(optional=True)

    def __init__(self, **kwargs):
        kwargs['codes'] = CodesNSL(kwargs['codes'])
        Location.__init__(self, **kwargs)

    @property
    def time_span(self):
        return (self.tmin, self.tmax)

    def get_pyrocko_station(self):
        from pyrocko import model
        return model.Station(*self._get_pyrocko_station_args())

    def _get_pyrocko_station_args(self):
        return (
            self.codes.network,
            self.codes.station,
            self.codes.location,
            self.lat,
            self.lon,
            self.elevation,
            self.depth,
            self.north_shift,
            self.east_shift)


class Sensor(Location):
    '''
    Representation of a channel group.
    '''

    codes = CodesNSLCE.T()

    tmin = Timestamp.T(optional=True)
    tmax = Timestamp.T(optional=True)

    deltat = Float.T(optional=True)

    @property
    def time_span(self):
        return (self.tmin, self.tmax)

    def __init__(self, **kwargs):
        kwargs['codes'] = CodesNSLCE(kwargs['codes'])
        Location.__init__(self, **kwargs)

    def _get_sensor_args(self):
        def getattr_rep(k):
            if k == 'codes':
                return self.codes.replace(
                    channel=self.codes.channel[:-1] + '?')
            else:
                return getattr(self, k)

        return tuple(getattr_rep(k) for k in Sensor.T.propnames)

    @classmethod
    def from_channels(cls, channels):
        groups = defaultdict(list)
        for channel in channels:
            groups[channel._get_sensor_args()].append(channel)

        return [
            cls(**dict((k, v) for (k, v) in zip(cls.T.propnames, args)))
            for args, _ in groups.items()]

    def _get_pyrocko_station_args(self):
        return (
            self.codes.network,
            self.codes.station,
            self.codes.location,
            self.lat,
            self.lon,
            self.elevation,
            self.depth,
            self.north_shift,
            self.east_shift)


@squirrel_content
class Channel(Sensor):
    '''
    A channel of a seismic station.
    '''

    dip = Float.T(optional=True)
    azimuth = Float.T(optional=True)

    @classmethod
    def from_channels(cls, channels):
        raise NotImplementedError()

    def get_pyrocko_channel(self):
        from pyrocko import model
        return model.Channel(*self._get_pyrocko_channel_args())

    def _get_pyrocko_channel_args(self):
        return (
            self.codes.channel,
            self.azimuth,
            self.dip)


observational_quantities = [
    'acceleration', 'velocity', 'displacement', 'pressure', 'rotation',
    'temperature']


technical_quantities = [
    'voltage', 'counts']


class QuantityType(StringChoice):
    '''
    Choice of observational or technical quantity.

    SI units are used for all quantities, where applicable.
    '''
    choices = observational_quantities + technical_quantities


class ResponseStage(Object):
    '''
    Representation of a response stage.

    Components of a seismic recording system are represented as a sequence of
    response stages, e.g. sensor, pre-amplifier, digitizer, digital
    downsampling.
    '''
    input_quantity = QuantityType.T(optional=True)
    input_sample_rate = Float.T(optional=True)
    output_quantity = QuantityType.T(optional=True)
    output_sample_rate = Float.T(optional=True)
    elements = List.T(FrequencyResponse.T())
    log = List.T(Tuple.T(3, String.T()))

    @property
    def stage_type(self):
        if self.input_quantity in observational_quantities \
                and self.output_quantity in observational_quantities:
            return 'conversion'

        if self.input_quantity in observational_quantities \
                and self.output_quantity == 'voltage':
            return 'sensor'

        elif self.input_quantity == 'voltage' \
                and self.output_quantity == 'voltage':
            return 'electronics'

        elif self.input_quantity == 'voltage' \
                and self.output_quantity == 'counts':
            return 'digitizer'

        elif self.input_quantity == 'counts' \
                and self.output_quantity == 'counts' \
                and self.input_sample_rate != self.output_sample_rate:
            return 'decimation'

        elif self.input_quantity in observational_quantities \
                and self.output_quantity == 'counts':
            return 'combination'

        else:
            return 'unknown'

    @property
    def summary(self):
        irate = self.input_sample_rate
        orate = self.output_sample_rate
        factor = None
        if irate and orate:
            factor = irate / orate
        return 'ResponseStage, ' + (
            '%s%s => %s%s%s' % (
                self.input_quantity or '?',
                ' @ %g Hz' % irate if irate else '',
                self.output_quantity or '?',
                ' @ %g Hz' % orate if orate else '',
                ' :%g' % factor if factor else '')
        )

    def get_effective(self):
        return MultiplyResponse(responses=list(self.elements))


D = 'displacement'
V = 'velocity'
A = 'acceleration'

g_converters = {
    (V, D): IntegrationResponse(1),
    (A, D): IntegrationResponse(2),
    (D, V): DifferentiationResponse(1),
    (A, V): IntegrationResponse(1),
    (D, A): DifferentiationResponse(2),
    (V, A): DifferentiationResponse(1)}


def response_converters(input_quantity, output_quantity):
    if input_quantity is None or input_quantity == output_quantity:
        return []

    if output_quantity is None:
        raise ConversionError('Unspecified target quantity.')

    try:
        return [g_converters[input_quantity, output_quantity]]

    except KeyError:
        raise ConversionError('No rule to convert from "%s" to "%s".' % (
            input_quantity, output_quantity))


@squirrel_content
class Response(Object):
    '''
    The instrument response of a seismic station channel.
    '''

    codes = CodesNSLCE.T()
    tmin = Timestamp.T(optional=True)
    tmax = Timestamp.T(optional=True)

    stages = List.T(ResponseStage.T())
    checkpoints = List.T(FrequencyResponseCheckpoint.T())

    deltat = Float.T(optional=True)
    log = List.T(Tuple.T(3, String.T()))

    def __init__(self, **kwargs):
        kwargs['codes'] = CodesNSLCE(kwargs['codes'])
        Object.__init__(self, **kwargs)

    @property
    def time_span(self):
        return (self.tmin, self.tmax)

    @property
    def nstages(self):
        return len(self.stages)

    @property
    def input_quantity(self):
        return self.stages[0].input_quantity if self.stages else None

    @property
    def output_quantity(self):
        return self.stages[-1].input_quantity if self.stages else None

    @property
    def output_sample_rate(self):
        return self.stages[-1].output_sample_rate if self.stages else None

    @property
    def stages_summary(self):
        def grouped(xs):
            xs = list(xs)
            g = []
            for i in range(len(xs)):
                g.append(xs[i])
                if i+1 < len(xs) and xs[i+1] != xs[i]:
                    yield g
                    g = []

            if g:
                yield g

        return '+'.join(
            '%s%s' % (g[0], '(%i)' % len(g) if len(g) > 1 else '')
            for g in grouped(stage.stage_type for stage in self.stages))

    @property
    def summary(self):
        orate = self.output_sample_rate
        return '%s %-16s %s' % (
            self.__class__.__name__, self.str_codes, self.str_time_span) \
            + ', ' + ', '.join((
                '%s => %s' % (
                    self.input_quantity or '?', self.output_quantity or '?')
                + (' @ %g Hz' % orate if orate else ''),
                self.stages_summary,
            ))

    def get_effective(self, input_quantity=None):
        elements = response_converters(input_quantity, self.input_quantity)

        elements.extend(
            stage.get_effective() for stage in self.stages)

        return MultiplyResponse(responses=simplify_responses(elements))


@squirrel_content
class Event(Object):
    '''
    A seismic event.
    '''

    name = String.T(optional=True)
    time = Timestamp.T()
    duration = Float.T(optional=True)

    lat = Float.T()
    lon = Float.T()
    depth = Float.T(optional=True)

    magnitude = Float.T(optional=True)

    def get_pyrocko_event(self):
        from pyrocko import model
        model.Event(
            name=self.name,
            time=self.time,
            lat=self.lat,
            lon=self.lon,
            depth=self.depth,
            magnitude=self.magnitude,
            duration=self.duration)

    @property
    def time_span(self):
        return (self.time, self.time)


def ehash(s):
    return hashlib.sha1(s.encode('utf8')).hexdigest()


def random_name(n=8):
    return urlsafe_b64encode(urandom(n)).rstrip(b'=').decode('ascii')


@squirrel_content
class WaveformPromise(Object):
    '''
    Information about a waveform potentially downloadable from a remote site.

    In the Squirrel framework, waveform promises are used to permit download of
    selected waveforms from a remote site. They are typically generated by
    calls to
    :py:meth:`~pyrocko.squirrel.base.Squirrel.update_waveform_promises`.
    Waveform promises are inserted and indexed in the database similar to
    normal waveforms. When processing a waveform query, e.g. from
    :py:meth:`~pyrocko.squirrel.base.Squirrel.get_waveform`, and no local
    waveform is available for the queried time span, a matching promise can be
    resolved, i.e. an attempt is made to download the waveform from the remote
    site. The promise is removed after the download attempt (except when a
    network error occurs). This prevents Squirrel from making unnecessary
    queries for waveforms missing at the remote site.
    '''

    codes = CodesNSLCE.T()
    tmin = Timestamp.T()
    tmax = Timestamp.T()

    deltat = Float.T(optional=True)

    source_hash = String.T()

    def __init__(self, **kwargs):
        kwargs['codes'] = CodesNSLCE(kwargs['codes'])
        Object.__init__(self, **kwargs)

    @property
    def time_span(self):
        return (self.tmin, self.tmax)


class InvalidWaveform(Exception):
    pass


class WaveformOrder(Object):
    '''
    Waveform request information.
    '''

    source_id = String.T()
    codes = CodesNSLCE.T()
    deltat = Float.T()
    tmin = Timestamp.T()
    tmax = Timestamp.T()
    gaps = List.T(Tuple.T(2, Timestamp.T()))

    @property
    def client(self):
        return self.source_id.split(':')[1]

    def describe(self, site='?'):
        return '%s:%s %s [%s - %s]' % (
            self.client, site, str(self.codes),
            util.time_to_str(self.tmin), util.time_to_str(self.tmax))

    def validate(self, tr):
        if tr.ydata.size == 0:
            raise InvalidWaveform(
                'waveform with zero data samples')

        if tr.deltat != self.deltat:
            raise InvalidWaveform(
                'incorrect sampling interval - waveform: %g s, '
                'meta-data: %g s' % (
                    tr.deltat, self.deltat))

        if not num.all(num.isfinite(tr.ydata)):
            raise InvalidWaveform('waveform has NaN values')


def order_summary(orders):
    codes_list = sorted(set(order.codes for order in orders))
    if len(codes_list) > 3:
        return '%i order%s: %s - %s' % (
            len(orders),
            util.plural_s(orders),
            str(codes_list[0]),
            str(codes_list[1]))

    else:
        return '%i order%s: %s' % (
            len(orders),
            util.plural_s(orders),
            ', '.join(str(codes) for codes in codes_list))


class Nut(Object):
    '''
    Index entry referencing an elementary piece of content.

    So-called *nuts* are used in Pyrocko's Squirrel framework to hold common
    meta-information about individual pieces of waveforms, stations, channels,
    etc. together with the information where it was found or generated.
    '''

    file_path = String.T(optional=True)
    file_format = String.T(optional=True)
    file_mtime = Timestamp.T(optional=True)
    file_size = Int.T(optional=True)

    file_segment = Int.T(optional=True)
    file_element = Int.T(optional=True)

    kind_id = Int.T()
    codes = Codes.T()

    tmin_seconds = Int.T(default=0)
    tmin_offset = Int.T(default=0, optional=True)
    tmax_seconds = Int.T(default=0)
    tmax_offset = Int.T(default=0, optional=True)

    deltat = Float.T(default=0.0)

    content = Any.T(optional=True)

    content_in_db = False

    def __init__(
            self,
            file_path=None,
            file_format=None,
            file_mtime=None,
            file_size=None,
            file_segment=None,
            file_element=None,
            kind_id=0,
            codes=CodesX(''),
            tmin_seconds=None,
            tmin_offset=0,
            tmax_seconds=None,
            tmax_offset=0,
            deltat=None,
            content=None,
            tmin=None,
            tmax=None,
            values_nocheck=None):

        if values_nocheck is not None:
            (self.file_path, self.file_format, self.file_mtime,
             self.file_size,
             self.file_segment, self.file_element,
             self.kind_id, codes_safe_str,
             self.tmin_seconds, self.tmin_offset,
             self.tmax_seconds, self.tmax_offset,
             self.deltat) = values_nocheck

            self.codes = to_codes_simple(self.kind_id, codes_safe_str)
            self.content = None
        else:
            if tmin is not None:
                tmin_seconds, tmin_offset = tsplit(tmin)

            if tmax is not None:
                tmax_seconds, tmax_offset = tsplit(tmax)

            self.kind_id = int(kind_id)
            self.codes = codes
            self.tmin_seconds = int_or_g_tmin(tmin_seconds)
            self.tmin_offset = int(tmin_offset)
            self.tmax_seconds = int_or_g_tmax(tmax_seconds)
            self.tmax_offset = int(tmax_offset)
            self.deltat = float_or_none(deltat)
            self.file_path = str_or_none(file_path)
            self.file_segment = int_or_none(file_segment)
            self.file_element = int_or_none(file_element)
            self.file_format = str_or_none(file_format)
            self.file_mtime = float_or_none(file_mtime)
            self.file_size = int_or_none(file_size)
            self.content = content

        Object.__init__(self, init_props=False)

    def __eq__(self, other):
        return (isinstance(other, Nut) and
                self.equality_values == other.equality_values)

    def hash(self):
        return ehash(','.join(str(x) for x in self.key))

    def __ne__(self, other):
        return not (self == other)

    def get_io_backend(self):
        from . import io
        return io.get_backend(self.file_format)

    def file_modified(self):
        return self.get_io_backend().get_stats(self.file_path) \
            != (self.file_mtime, self.file_size)

    @property
    def dkey(self):
        return (self.kind_id, self.tmin_seconds, self.tmin_offset, self.codes)

    @property
    def key(self):
        return (
            self.file_path,
            self.file_segment,
            self.file_element,
            self.file_mtime)

    @property
    def equality_values(self):
        return (
            self.file_segment, self.file_element,
            self.kind_id, self.codes,
            self.tmin_seconds, self.tmin_offset,
            self.tmax_seconds, self.tmax_offset, self.deltat)

    @property
    def tmin(self):
        return tjoin(self.tmin_seconds, self.tmin_offset)

    @tmin.setter
    def tmin(self, t):
        self.tmin_seconds, self.tmin_offset = tsplit(t)

    @property
    def tmax(self):
        return tjoin(self.tmax_seconds, self.tmax_offset)

    @tmax.setter
    def tmax(self, t):
        self.tmax_seconds, self.tmax_offset = tsplit(t)

    @property
    def kscale(self):
        if self.tmin_seconds is None or self.tmax_seconds is None:
            return 0
        return tscale_to_kscale(self.tmax_seconds - self.tmin_seconds)

    @property
    def waveform_kwargs(self):
        network, station, location, channel, extra = self.codes

        return dict(
            network=network,
            station=station,
            location=location,
            channel=channel,
            extra=extra,
            tmin=self.tmin,
            tmax=self.tmax,
            deltat=self.deltat)

    @property
    def waveform_promise_kwargs(self):
        return dict(
            codes=self.codes,
            tmin=self.tmin,
            tmax=self.tmax,
            deltat=self.deltat)

    @property
    def station_kwargs(self):
        network, station, location = self.codes
        return dict(
            codes=self.codes,
            tmin=tmin_or_none(self.tmin),
            tmax=tmax_or_none(self.tmax))

    @property
    def channel_kwargs(self):
        network, station, location, channel, extra = self.codes
        return dict(
            codes=self.codes,
            tmin=tmin_or_none(self.tmin),
            tmax=tmax_or_none(self.tmax),
            deltat=self.deltat)

    @property
    def response_kwargs(self):
        return dict(
            codes=self.codes,
            tmin=tmin_or_none(self.tmin),
            tmax=tmax_or_none(self.tmax),
            deltat=self.deltat)

    @property
    def event_kwargs(self):
        return dict(
            name=self.codes,
            time=self.tmin,
            duration=(self.tmax - self.tmin) or None)

    @property
    def trace_kwargs(self):
        network, station, location, channel, extra = self.codes

        return dict(
            network=network,
            station=station,
            location=location,
            channel=channel,
            extra=extra,
            tmin=self.tmin,
            tmax=self.tmax-self.deltat,
            deltat=self.deltat)

    @property
    def dummy_trace(self):
        return DummyTrace(self)

    @property
    def summary(self):
        if self.tmin == self.tmax:
            ts = util.time_to_str(self.tmin)
        else:
            ts = '%s - %s' % (
                util.time_to_str(self.tmin),
                util.time_to_str(self.tmax))

        return ' '.join((
            ('%s,' % to_kind(self.kind_id)).ljust(9),
            ('%s,' % str(self.codes)).ljust(18),
            ts))


def make_waveform_nut(**kwargs):
    return Nut(kind_id=WAVEFORM, **kwargs)


def make_waveform_promise_nut(**kwargs):
    return Nut(kind_id=WAVEFORM_PROMISE, **kwargs)


def make_station_nut(**kwargs):
    return Nut(kind_id=STATION, **kwargs)


def make_channel_nut(**kwargs):
    return Nut(kind_id=CHANNEL, **kwargs)


def make_response_nut(**kwargs):
    return Nut(kind_id=RESPONSE, **kwargs)


def make_event_nut(**kwargs):
    return Nut(kind_id=EVENT, **kwargs)


def group_channels(nuts):
    by_ansl = {}
    for nut in nuts:
        if nut.kind_id != CHANNEL:
            continue

        ansl = nut.codes[:4]

        if ansl not in by_ansl:
            by_ansl[ansl] = {}

        group = by_ansl[ansl]

        k = nut.codes[4][:-1], nut.deltat, nut.tmin, nut.tmax

        if k not in group:
            group[k] = set()

        group.add(nut.codes[4])

    return by_ansl


class DummyTrace(object):

    def __init__(self, nut):
        self.nut = nut
        self.codes = nut.codes
        self.meta = {}

    @property
    def tmin(self):
        return self.nut.tmin

    @property
    def tmax(self):
        return self.nut.tmax

    @property
    def deltat(self):
        return self.nut.deltat

    @property
    def nslc_id(self):
        return self.codes.nslc

    @property
    def network(self):
        return self.codes.network

    @property
    def station(self):
        return self.codes.station

    @property
    def location(self):
        return self.codes.location

    @property
    def channel(self):
        return self.codes.channel

    @property
    def extra(self):
        return self.codes.extra

    def overlaps(self, tmin, tmax):
        return not (tmax < self.nut.tmin or self.nut.tmax < tmin)


def duration_to_str(t):
    if t > 24*3600:
        return '%gd' % (t / (24.*3600.))
    elif t > 3600:
        return '%gh' % (t / 3600.)
    elif t > 60:
        return '%gm' % (t / 60.)
    else:
        return '%gs' % t


class Coverage(Object):
    '''
    Information about times covered by a waveform or other time series data.
    '''
    kind_id = Int.T(
        help='Content type.')
    pattern = Codes.T(
        help='The codes pattern in the request, which caused this entry to '
             'match.')
    codes = Codes.T(
        help='NSLCE or NSL codes identifier of the time series.')
    deltat = Float.T(
        help='Sampling interval [s]',
        optional=True)
    tmin = Timestamp.T(
        help='Global start time of time series.',
        optional=True)
    tmax = Timestamp.T(
        help='Global end time of time series.',
        optional=True)
    changes = List.T(
        Tuple.T(2, Any.T()),
        help='List of change points, with entries of the form '
             '``(time, count)``, where a ``count`` of zero indicates start of '
             'a gap, a value of 1 start of normal data coverage and a higher '
             'value duplicate or redundant data coverage.')

    @classmethod
    def from_values(cls, args):
        pattern, codes, deltat, tmin, tmax, changes, kind_id = args
        return cls(
            kind_id=kind_id,
            pattern=pattern,
            codes=codes,
            deltat=deltat,
            tmin=tmin,
            tmax=tmax,
            changes=changes)

    @property
    def summary(self):
        ts = '%s - %s,' % (
            util.time_to_str(self.tmin),
            util.time_to_str(self.tmax))

        srate = self.sample_rate

        return ' '.join((
            ('%s,' % to_kind(self.kind_id)).ljust(9),
            ('%s,' % str(self.codes)).ljust(18),
            ts,
            '%10.3g,' % srate if srate else '',
            '%4i' % len(self.changes),
            '%s' % duration_to_str(self.total)))

    @property
    def sample_rate(self):
        if self.deltat is None:
            return None
        elif self.deltat == 0.0:
            return 0.0
        else:
            return 1.0 / self.deltat

    @property
    def labels(self):
        srate = self.sample_rate
        return (
            ('%s' % str(self.codes)),
            '%.3g' % srate if srate else '')

    @property
    def total(self):
        total_t = None
        for tmin, tmax, _ in self.iter_spans():
            total_t = (total_t or 0.0) + (tmax - tmin)

        return total_t

    def iter_spans(self):
        last = None
        for (t, count) in self.changes:
            if last is not None:
                last_t, last_count = last
                if last_count > 0:
                    yield last_t, t, last_count

            last = (t, count)


__all__ = [
    'to_codes',
    'to_codes_guess',
    'to_codes_simple',
    'to_kind',
    'to_kinds',
    'to_kind_id',
    'to_kind_ids',
    'CodesError',
    'Codes',
    'CodesNSLCE',
    'CodesNSL',
    'CodesX',
    'Station',
    'Channel',
    'Sensor',
    'Response',
    'Nut',
    'Coverage',
    'WaveformPromise',
]
