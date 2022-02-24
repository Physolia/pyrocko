#!/usr/bin/env python3
import numpy as np
from pyrocko.util import time_to_str as tts
from pyrocko import squirrel


def rms(data):
    return np.sqrt(np.sum(data**2))


class ReportRMSTool(squirrel.SquirrelCommand):

    def setup(self, parser):
        self.add_selection_arguments(parser)

        # Add '--codes', '--tmin' and '--tmax', but not '--time'.
        self.add_query_arguments(parser, without=['time'])

        parser.add_argument(
            '--fmin',
            dest='fmin',
            metavar='FLOAT',
            type=float,
            help='Corner of highpass [Hz].')

        parser.add_argument(
            '--fmax',
            dest='fmax',
            metavar='FLOAT',
            type=float,
            help='Corner of lowpass [Hz].')

    def call(self, parser, args):
        sq = self.squirrel_from_selection_arguments(args)

        fmin = args.fmin
        fmax = args.fmax

        query_args = self.squirrel_query_from_arguments(args)
        sq.update(**query_args)
        sq.update_waveform_promises(**query_args)

        for batch in sq.chopper_waveforms(
                tinc=3600.,
                tpad=1.0/fmin if fmin is not None else 0.0,
                want_incomplete=False,
                snap_window=True,
                **query_args):

            for tr in batch.traces:

                if fmin is not None:
                    tr.highpass(4, fmin)

                if fmax is not None:
                    tr.lowpass(4, fmax)

                tr.chop(batch.tmin, batch.tmax)
                print(tr.str_codes, tts(batch.tmin), rms(tr.ydata))


squirrel.from_command(
    ReportRMSTool(),
    description='Report hourly RMS values.')
