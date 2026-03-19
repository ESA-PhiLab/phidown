Contributing
============

Contributions are welcome.

Development Setup
-----------------

Clone the repository and install the local environment:

.. code-block:: bash

   git clone https://github.com/ESA-PhiLab/phidown.git
   cd phidown
   pdm install

If you prefer ``pip``:

.. code-block:: bash

   pip install -e ".[dev,test,docs,viz,ais]"

Current Tooling
---------------

The repository currently declares these core development tools:

* ``pytest`` and ``pytest-mock`` for tests
* ``flake8`` for linting
* Sphinx for documentation builds

Running Tests
-------------

.. code-block:: bash

   pytest

Run a specific file:

.. code-block:: bash

   pytest tests/test_search.py

Linting
-------

.. code-block:: bash

   flake8 phidown tests

Documentation
-------------

Build the docs locally from the ``docs`` directory:

.. code-block:: bash

   cd docs
   python3 -m pip install -r requirements.txt
   make html

Contribution Checklist
----------------------

Before opening a pull request:

* Keep changes focused and well-scoped
* Add or update tests when behavior changes
* Update documentation for user-facing changes
* Run ``pytest`` and ``flake8`` locally when possible

PR Notes
--------

Include a concise description of:

* What changed
* Why it changed
* How you verified it
