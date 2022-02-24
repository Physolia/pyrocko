
Squirrel API usage
==================

.. _squirrel_cli_example:

A complete example: calculate hourly RMS values
-----------------------------------------------

In this tutorial we will write a user-friendly command line interface (CLI)
program to calculate hourly root-mean-square (RMS) values for continuous
seismic waveform recordings. Many methods in seismology process waveform
recordings in similar ways and so this example can serve as a design pattern
for tools like daily spectrograms, PSD plots, drum plots, earthquake detectors,
automatic pickers, and so on. We will show different styles of writing such a
script/app, each useful in slightly different situations. If you use the
provided building blocks and follow the conventions laid out below, your app
will immediately feel familiar to other Squirrel users. And it will ship with a
bunch of nice features, like support for extra large datasets. And it will be
pleasure to maintain.

**Specs for the tutorial app:**

- Calculate hourly RMS values.
- Get data from local file collection or from online FDSN web services.
- Keep and reuse downloaded raw data (don't download same data twice).
- Process a given time span.
- Station/channel selection.
- Efficiently hop through the data in chunks of one hour
- Always start chunks at full hour.
- Bandpass filter data before calculating RMS.
- Extinguish filter artifacts by use of overlapping time windows.

.. _squirrel_quick_and_dirty:

Variant 1: quick and dirty script
.................................

You feel like hard-coding today? Sometimes we do not need any sophisticated CLI
or configuration files.

Here's a commented solution to the RMS calculation task. Study carefully -
there is a lot of functionality packed into this short script.

.. literalinclude :: /../../examples/squirrel_rms1.py
    :caption: :download:`squirrel_rms1.py </../../examples/squirrel_rms1.py>`
    :language: python

.. note::

   In the code above, we have shown three different ways of restricting the
   channels to be processed. Each of these narrows down the set of channels
   available but they have very different effects:

   - The ``query_args`` argument of :py:meth:`sq.add_fdsn()
     <pyrocko.squirrel.base.Squirrel.add_fdsn>` restricts the meta-data known
     to Squirrel by limiting what is fetched from the `FDSN station web service
     <https://www.fdsn.org/webservices/fdsnws-station-1.1.pdf>`_. Using
     ``query_args`` has the benefit of reducing the size of the meta-data to
     transmit and parse. However changing it later will result in new queries
     to be made. If unchanged, the locally cached meta-data will be used when
     the program is rerun.
   - By calling :py:meth:`sq.update_waveform_promises()
     <pyrocko.squirrel.base.Squirrel.update_waveform_promises>` we give
     Squirrel permission to download certain waveforms by creating so-called
     *waveform promises* for matching channels and time intervals. If we call
     the method without specifying the ``codes`` argument, waveforms from all
     stations/channels are marked as downloadable. Squirrel will not download
     anything if we do not call :py:meth:`sq.update_waveform_promises()
     <pyrocko.squirrel.base.Squirrel.update_waveform_promises>`.
   - The ``codes`` argument of :py:meth:`sq.chopper_waveforms()
     <pyrocko.squirrel.base.Squirrel.chopper_waveforms>` selects from the
     waveforms we have locally and from the `waveform promises` set up earlier.
     Downloading will happen just as needed and in chunks of reasonable size.

Before we actually run the script we will first create a local Squirrel
environment, so that all the downloaded files as well as the database are
stored in the current directory under :file:`.squirrel/`. This will make it
easier to clean up when we are done (``rm -rf .squirrel/``). If we omit this
step, the user's global Squirrel environment
(:file:`~/.pyrocko/cache/squirrel/`) is used.

Create local environment (optional):

.. code-block:: shell-session

    $ squirrel init

And now let's run our script:

.. code-block:: shell-session

    $ python squirrel_rms1.py
    [...]
    squirrel_rms1.py:psq.client.fdsn - INFO - FDSN "bgr" metadata: querying...
    squirrel_rms1.py:psq.client.fdsn - INFO - FDSN "bgr" metadata: new (expires: never)
    [...]
    squirrel_rms1.py:psq.base        - INFO - Waveform orders standing for download: 1 (1)
    squirrel_rms1.py:psq.client.fdsn - INFO - FDSN "bgr" waveforms: downloading, 1 order: GR.BFO..LHZ
    squirrel_rms1.py:psq.client.fdsn - INFO - FDSN "bgr" waveforms: 1 download successful
    [...]
    GR.BFO..LHZ. 2022-01-14 00:00:00.000 1663.1710971934713
    GR.BFO..LHZ. 2022-01-14 01:00:00.000 1773.5581525847992
    GR.BFO..LHZ. 2022-01-14 02:00:00.000 1688.5986175096787
    [...]
    squirrel_rms1.py:psq.base        - INFO - Waveform orders standing for download: 1 (1)
    squirrel_rms1.py:psq.client.fdsn - INFO - FDSN "bgr" waveforms: downloading, 1 order: GR.BFO..LHZ
    squirrel_rms1.py:psq.client.fdsn - INFO - FDSN "bgr" waveforms: 1 download successful
    GR.BFO..LHZ. 2022-01-14 22:00:00.000 1570.7909549562307
    GR.BFO..LHZ. 2022-01-14 23:00:00.000 1595.3630840478215
    GR.BFO..LHZ. 2022-01-15 00:00:00.000 1445.7303611595091
    [...]

Excellent! It is downloading waveform data and calculating RMS values.

The lines with the RMS values are printed to *stdout*, while log messages go to
*stderr*. Like this, we could for example redirect only the RMS results to a
file but still see the log messages in the terminal:

.. code-block:: shell-session

    $ python squirrel_rms1.py > rms-GR.BFO..LHZ.txt

Running the script a second time is way faster, because nothing has to be
downloaded.

Not very flexible though with all the hard-coded settings in the script. Read
on to see how we can configure data access from the command line.

Variant 2: command line app (simple)
....................................

Instead of hard-coding the data sources in the script, we could set them with
command line arguments. The :py:mod:`pyrocko.squirrel.tool` module offers
functionality to set up our program so that it accepts the same options and
arguments like for example ``squirrel scan``. Here's the complete program after
changing to this to use :py:func:`~pyrocko.squirrel.tool.from_command`:

.. literalinclude :: /../../examples/squirrel_rms2.py
    :caption: :download:`squirrel_rms2.py </../../examples/squirrel_rms2.py>` - Notable differences to :ref:`Variant 1 <squirrel_quick_and_dirty>` highlighted.
    :language: python
    :emphasize-lines: 18-23

To get RMS values of some local data, we could run

.. code-block:: shell-session

    $ python squirrel_rms2.py data/2022

It is also self-documenting:

.. code-block:: shell-session

    $ python squirrel_rms2.py --help
    usage: examples/squirrel_rms2.py [--help] [--loglevel LEVEL] [--progress DEST]
                                 [--include REGEX] [--exclude REGEX]
                                 [--optimistic] [--format FORMAT]
                                 [--kind KINDS] [--persistent NAME] [--update]
                                 [--dataset FILE]
                                 [paths [paths ...]]

    Report hourly RMS values.

    Positional arguments:
      paths                 Files and directories with waveforms, metadata and
                            events.

    Optional arguments:
      --help, -h            Show this help message and exit.
      --loglevel LEVEL      Set logger level. Choices: critical, error, warning,
                            info, debug. Default: info.
      --progress DEST       Set how progress status is reported. Choices: terminal,
                            log, off. Default: terminal.

    [...]
    --dataset FILE, -d FILE
                        Add directories, files, remote sources from dataset
                        description file. This option can be repeated to add
                        multiple datasets. Run `squirrel template` to obtain
                        examples of dataset description files.

So, to use a remote data source we can create a dataset description file and
pass this to ``--dataset``. Examples of such dataset description files are
provided by the ``squirrel template`` command. By chance there already is an
example for accessing all LH channels from BGR FDSN web service! We can save
the example dataset description file with

.. code-block:: shell-session

    $ squirrel template bgr-gr-lh.dataset -w
    squirrel:psq.cli.template - INFO - File written: bgr-gr-lh.dataset.yaml

The dataset description is a nicely commented YAML file and we could modify it
to our liking.

.. code-block:: yaml
    :caption: bgr-gr-lh.dataset.yaml

    --- !squirrel.Dataset

    # All file paths given below are treated relative to the location of this
    # configuration file. Here we may give a common prefix. For example, if the
    # configuration file is in the sub-directory 'PROJECT/config/', set it to '..'
    # so that all paths are relative to 'PROJECT/'.
    path_prefix: '.'

    # Data sources to be added (LocalData, FDSNSource, CatalogSource, ...)
    sources:
    - !squirrel.FDSNSource

      # URL or alias of FDSN site.
      site: bgr

      # FDSN query arguments to make metadata queries.
      # See http://www.fdsn.org/webservices/fdsnws-station-1.1.pdf
      # Time span arguments should not be added here, because they are handled
      # automatically by Squirrel.
      query_args:
        network: 'GR'
        channel: 'LH?'

To calculate RMS values for the configured dataset, we can now run

.. code-block:: shell-session

    $ python squirrel_rms2.py --dataset bgr-gr-lh.dataset.yaml
    [...]
    GR.BFO..LHZ. 2022-01-14 00:00:00.000 1663.1710971934713
    GR.BFO..LHZ. 2022-01-14 01:00:00.000 1773.5581525847992
    GR.BFO..LHZ. 2022-01-14 02:00:00.000 1688.5986175096787
    [...]

This is a bit more flexible because we can now easily exchange the data used
from the command line. But there is still room for improvements. Read on to see
how we can add our own options to the program's command line interface.

.. _squirrel_cli_tight_single:

Variant 3a: command line app (tight integration, single-command)
................................................................

.. literalinclude :: /../../examples/squirrel_rms3a.py
    :caption: :download:`squirrel_rms3a.py </../../examples/squirrel_rms3a.py>`
    :language: python

Variant 3b: command line app (tight integration, multi-command)
...............................................................

.. literalinclude :: /../../examples/squirrel_rms3b.py
    :caption: :download:`squirrel_rms3b.py </../../examples/squirrel_rms3b.py>` - Differences to :ref:`Variant 3a <squirrel_cli_tight_single>` highlighted.
    :language: python
    :emphasize-lines: 13-15, 67-

Variant 4: command line app (loose integration)
...............................................

.. literalinclude :: /../../examples/squirrel_rms4.py
    :caption: :download:`squirrel_rms4.py </../../examples/squirrel_rms4.py>`
    :language: python
