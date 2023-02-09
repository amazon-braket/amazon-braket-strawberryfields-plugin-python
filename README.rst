Amazon Braket Strawberry Fields Plugin
######################################

.. image:: https://img.shields.io/pypi/v/amazon-braket-strawberryfields-plugin.svg
    :alt: Latest Version
    :target: https://pypi.python.org/pypi/amazon-braket-strawberryfields-plugin
.. image:: https://img.shields.io/pypi/pyversions/amazon-braket-strawberryfields-plugin.svg
    :alt: Supported Python Versions
    :target: https://pypi.python.org/pypi/amazon-braket-strawberryfields-plugin
.. image:: https://img.shields.io/github/actions/workflow/status/aws/amazon-braket-strawberryfields-plugin-python/python-package.yml?branch=main&logo=github
    :alt: Build Status
    :target: https://github.com/aws/amazon-braket-strawberryfields-plugin-python/actions?query=workflow%3A%22Python+package%22
.. image:: https://codecov.io/gh/aws/amazon-braket-strawberryfields-plugin-python/branch/main/graph/badge.svg?token=VPPM8BJKW4
    :alt: codecov
    :target: https://codecov.io/gh/aws/amazon-braket-strawberryfields-plugin-python
.. image:: https://img.shields.io/readthedocs/amazon-braket-strawberryfields-plugin-python.svg?logo=read-the-docs
    :alt: Documentation Status
    :target: https://amazon-braket-strawberryfields-plugin-python.readthedocs.io/en/latest/?badge=latest
.. image:: https://img.shields.io/badge/code_style-black-000000.svg
    :alt: Code Style: Black
    :target: https://github.com/psf/black

This plugin provides a ``BraketEngine`` class for running photonic quantum circuits created in Strawberry Fields on the Amazon Braket service.

.. header-start-inclusion-marker-do-not-remove

The `Amazon Braket Python SDK <https://github.com/aws/amazon-braket-sdk-python>`__ is an open source
library that provides a framework to interact with quantum computing hardware
devices and simulators through Amazon Braket.

`Strawberry Fields <https://strawberryfields.readthedocs.io>`__ is an open source library for writing
and running programs for photonic quantum computers.

.. header-end-inclusion-marker-do-not-remove

The plugin documentation can be found here: `<https://amazon-braket-strawberryfields-plugin-python.readthedocs.io/en/latest/>`__.

Features
========

This plugin provides the classes ``BraketEngine`` for submitting photonic circuits to Amazon Braket and ``BraketJob`` for tracking the status of the Braket task.

``BraketEngine`` and ``BraketJob`` have the same interfaces as ``RemoteEngine`` in Strawberry Fields and ``Job`` in the Xanadu Cloud Client, respectively, and can be used as drop-in replacements:

.. code-block:: python

    from braket.strawberryfields_plugin import BraketEngine

    eng = BraketEngine("arn:aws:braket:us-east-1::device/qpu/xanadu/Borealis")
    result = eng.run(prog, shots=1000)  # Synchronous, returns sf.Result
    job = eng.run_async(prog, shots=1000)  # Asychronous, returns BraketJob
    print(job.status)


.. installation-start-inclusion-marker-do-not-remove

Installation
============

Before you begin working with the Amazon Braket Strawberry Fields Plugin, make sure 
that you installed or configured the following prerequisites:


* Download and install `Python 3.7.2 <https://www.python.org/downloads/>`__ or greater.
  If you are using Windows, choose the option *Add Python to environment variables* before you begin the installation.

* Make sure that your AWS account is onboarded to Amazon Braket, as per the instructions
  `here <https://github.com/aws/amazon-braket-sdk-python#prerequisites>`__.

* Download and install `Strawberry Fields <https://strawberryfields.readthedocs.io/en/stable/_static/install.html>`__:

  .. code-block:: bash

      pip install strawberryfields


You can then install the latest release of the Strawberry Fields-Braket plugin as follows:

.. code-block:: bash

    pip install amazon-braket-strawberryfields-plugin


You can also install the development version from source by cloning this repository and running a 
pip install command in the root directory of the repository:

.. code-block:: bash

    git clone https://github.com/aws/amazon-braket-strawberryfields-plugin-python.git
    cd amazon-braket-strawberryfields-plugin-python
    pip install .


You can check your currently installed version of ``amazon-braket-strawberryfields-plugin`` with ``pip show``:

.. code-block:: bash

    pip show amazon-braket-strawberryfields-plugin


or alternatively from within Python:

.. code-block:: python

    from braket import strawberryfields_plugin
    strawberryfields_plugin.__version__

Tests
~~~~~

Make sure to install test dependencies first:

.. code-block:: bash

    pip install -e "amazon-braket-strawberryfields-plugin-python[test]"

Unit tests
**********

Run the unit tests using:

.. code-block:: bash

    tox -e unit-tests


To run an individual test:

.. code-block:: bash

    tox -e unit-tests -- -k 'your_test'


To run linters and unit tests:

.. code-block:: bash

    tox

Integration tests
*****************

To run the integration tests, set the ``AWS_PROFILE`` as explained in the amazon-braket-sdk-python
`README <https://github.com/aws/amazon-braket-sdk-python/blob/main/README.md>`__:

.. code-block:: bash

    export AWS_PROFILE=Your_Profile_Name


Run the integration tests with:

.. code-block:: bash

    tox -e integ-tests

To run an individual integration test:

.. code-block:: bash

    tox -e integ-tests -- -k 'your_test'

Documentation
~~~~~~~~~~~~~

To build the HTML documentation, run:

.. code-block:: bash

  tox -e docs

The documentation can then be found in the ``doc/build/documentation/html/`` directory.

.. installation-end-inclusion-marker-do-not-remove

Contributing
============

We welcome contributions - simply fork the repository of this plugin, and then make a
`pull request <https://help.github.com/articles/about-pull-requests/>`__ containing your contribution.
All contributers to this plugin will be listed as authors on the releases.

We also encourage bug reports, suggestions for new features and enhancements, and even links to cool projects
or applications built with the plugin.

.. support-start-inclusion-marker-do-not-remove

Support
=======

- **Source Code:** https://github.com/aws/amazon-braket-strawberryfields-plugin-python
- **Issue Tracker:** https://github.com/aws/amazon-braket-strawberryfields-plugin-python/issues
- **Strawberry Fields Forum:** https://discuss.strawberryfields.ai

If you are having issues, please let us know by posting the issue on our Github issue tracker, or
by asking a question in the forum.

.. support-end-inclusion-marker-do-not-remove

.. license-start-inclusion-marker-do-not-remove

License
=======

This project is licensed under the Apache-2.0 License.

.. license-end-inclusion-marker-do-not-remove
