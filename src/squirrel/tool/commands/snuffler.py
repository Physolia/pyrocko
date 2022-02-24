# http://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------

from __future__ import absolute_import, print_function


def setup_subcommand(subparsers):
    return subparsers.add_parser(
        'snuffler',
        help='View in Snuffler.')


def setup(parser):
    parser.add_squirrel_selection_arguments()


def call(parser, args):
    squirrel = args.make_squirrel()
    squirrel.pile.snuffle()
