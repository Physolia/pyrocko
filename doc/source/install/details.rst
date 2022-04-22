Detailed installation instructions
==================================

Pyrocko can be installed under any operating system where its prerequisites are
available. This document describes details about its requirements which are
needed when a standard install is not possible or conflicts arise.

**For standard install instructions, head on over to**

* :doc:`system/index`

Prerequisites
-------------

The following software packages must be installed before Pyrocko can be
installed from source:

* Build requirements
   * C compiler (tested with gcc, clang and MSVC)
   * ``patch`` utility
   * `NumPy <http://numpy.scipy.org/>`_ (>= 1.6, with development headers)

* Try to use normal system packages for these Python modules:
   * `Python <http://www.python.org/>`_ (>= 3.5, with development headers)
   * `NumPy <http://numpy.scipy.org/>`_ (>= 1.6, with development headers)
   * `SciPy <http://scipy.org/>`_
   * `matplotlib <http://matplotlib.sourceforge.net/>`_ (with Qt4 or Qt5 backend)
   * `pyyaml <https://bitbucket.org/xi/pyyaml>`_
   * `PyQt4 or PyQt5 <http://www.riverbankcomputing.co.uk/software/pyqt/intro>`_ (only needed for the GUI apps)
   * `requests <http://docs.python-requests.org/en/master/>`_

* Optional Python modules:
   * `progressbar2 <http://pypi.python.org/pypi/progressbar2>`_
   * `Jinja2 <http://jinja.pocoo.org/>`_ (required for the :ref:`fomosto report <fomosto_report>` subcommand)
   * `nosetests <https://pypi.python.org/pypi/nose>`_ (to run the unittests)
   * `coverage <https://pypi.python.org/pypi/coverage>`_ (unittest coverage report)

* Manually install these optional software tools:
   * `GMT <http://gmt.soest.hawaii.edu/>`_ (4 or 5, only required for the :py:mod:`pyrocko.plot.automap` module)
   * `slinktool <http://www.iris.edu/data/dmc-seedlink.htm>`_ (optionally, if you want to use the :py:mod:`pyrocko.streaming.slink` module)
   * `rdseed <http://www.iris.edu/software/downloads/rdseed_request.htm>`_ (optionally, if you want to use the :py:mod:`pyrocko.io.rdseed` module)
   * `QSEIS <https://git.pyrocko.org/pyrocko/fomosto-qseis>`_ (optional, needed for the Fomosto ``qseis.2006a`` backend)
   * `QSSP <https://git.pyrocko.org/pyrocko/fomosto-qssp>`_ (optional, needed for the Fomosto ``qssp.2010`` backend)
   * `PSGRN/PSCMP <https://git.pyrocko.org/pyrocko/fomosto-psgrn-pscmp>`_ (optional, needed for the Fomosto ``psgrn.pscmp`` backend)

Download, compile and install Pyrocko from source
-------------------------------------------------

The following examples will install Pyrocko system-wide with Python 3 on Linux
or MacOS. For Windows source installs, please refer to :ref:`Installation on
Windows: From source <windows-install-from-source>`.

.. highlight:: sh

Use ``git`` to download the software package and the included script ``setup.py``
to install::

    cd ~/src/   # or wherever you keep your source packages
    git clone https://git.pyrocko.org/pyrocko/pyrocko.git pyrocko
    cd pyrocko
    # for single user:
    python3 setup.py install --user
    # system wide:
    sudo python3 setup.py install

**Note:** If you have previously installed Pyrocko using other tools like e.g.
*easy_install*, *pip*, or *conda*, you should first remove the old
installation. Otherwise you will end up with two parallel installations which
will cause trouble.

Updating
--------

If you later would like to update Pyrocko, run the following commands (this
assumes that you have used *git* to download Pyrocko):: 

    cd ~/src/pyrocko   # assuming the Pyrocko source package is here
    git pull origin master --ff-only
    # for single user:
    python3 setup.py install --user
    # system wide:
    sudo python3 setup.py install
