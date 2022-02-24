# http://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------

from __future__ import absolute_import, print_function


def setup_subcommand(subparsers):
    return subparsers.add_parser(
        'files',
        help='Lookup files providing given content selection.')


def setup(parser):
    parser.add_argument(
        '--relative',
        action='store_true',
        default=False,
        help='Reveal path as it is stored in the database. This is relative '
             'for files inside a Squirrel environment.')

    parser.add_squirrel_selection_arguments()
    parser.add_squirrel_query_arguments()


def call(parser, args):
    d = args.squirrel_query
    squirrel = args.make_squirrel()

    paths = set()
    if d:
        for nut in squirrel.iter_nuts(**d):
            paths.add(nut.file_path)

        db = squirrel.get_database()
        for path in sorted(paths):
            print(db.relpath(path) if args.relative else path)

    else:
        for path in squirrel.iter_paths(raw=args.relative):
            print(path)
