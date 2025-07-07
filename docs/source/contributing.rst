Contributing
============

We welcome contributions to Φ-Down! This guide explains how to contribute to the project.

Getting Started
---------------

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:

   .. code-block:: bash

      git clone https://github.com/YOUR_USERNAME/phidown.git
      cd phidown

3. **Set up development environment**:

   .. code-block:: bash

      # Install PDM (recommended)
      pip install pdm
      
      # Install development dependencies
      pdm install
      
      # Or use pip
      pip install -e .[dev,viz]

4. **Create a feature branch**:

   .. code-block:: bash

      git checkout -b feature/your-feature-name

Development Setup
-----------------

Development Tools
^^^^^^^^^^^^^^^^^

The project uses several tools for development:

* **PDM**: Dependency management and packaging
* **pytest**: Testing framework
* **flake8**: Code linting
* **black**: Code formatting
* **mypy**: Type checking
* **pre-commit**: Git hooks for code quality

Setting Up Pre-commit
^^^^^^^^^^^^^^^^^^^^^^

Install pre-commit hooks to ensure code quality:

.. code-block:: bash

   # Install pre-commit
   pip install pre-commit
   
   # Install hooks
   pre-commit install

Virtual Environment
^^^^^^^^^^^^^^^^^^^

Using PDM (recommended):

.. code-block:: bash

   pdm venv create
   pdm use  # Select the created environment
   pdm install

Using pip:

.. code-block:: bash

   python -m venv phidown-dev
   source phidown-dev/bin/activate  # On Windows: phidown-dev\\Scripts\\activate
   pip install -e .[dev,viz]

Running Tests
-------------

Run the test suite to ensure everything works:

.. code-block:: bash

   # Run all tests
   pytest
   
   # Run with coverage
   pytest --cov=phidown
   
   # Run specific test file
   pytest tests/test_search.py
   
   # Run specific test
   pytest tests/test_search.py::test_basic_search

Writing Tests
^^^^^^^^^^^^^

* Write tests for new functionality
* Follow existing test patterns
* Use descriptive test names
* Include edge cases and error conditions

Example test:

.. code-block:: python

   def test_search_with_valid_parameters():
       """Test search with valid parameters returns results."""
       searcher = CopernicusDataSearcher()
       results = searcher.search(
           collection_name='SENTINEL-2',
           start_date='2023-01-01',
           end_date='2023-01-31'
       )
       assert isinstance(results, pd.DataFrame)
       assert len(results) >= 0

Code Style
----------

We follow Python coding standards:

Formatting
^^^^^^^^^^

* Use **black** for code formatting
* Line length: 88 characters
* Use double quotes for strings
* Follow PEP 8 guidelines

.. code-block:: bash

   # Format code
   black phidown/
   
   # Check formatting
   black --check phidown/

Linting
^^^^^^^

* Use **flake8** for linting
* Fix all linting issues before submitting

.. code-block:: bash

   # Run linting
   flake8 phidown/
   
   # With specific configuration
   flake8 --config=.flake8 phidown/

Type Hints
^^^^^^^^^^

* Use type hints for all functions
* Use descriptive type annotations
* Follow Google docstring format

.. code-block:: python

   def search_products(
       collection_name: str,
       start_date: str,
       end_date: str
   ) -> pd.DataFrame:
       """Search for products in the given date range.
       
       Args:
           collection_name: Name of the satellite collection
           start_date: Start date in YYYY-MM-DD format
           end_date: End date in YYYY-MM-DD format
           
       Returns:
           DataFrame containing search results
           
       Raises:
           ValueError: If date format is invalid
       """
       pass

Documentation
-------------

Writing Documentation
^^^^^^^^^^^^^^^^^^^^^

* Use Google-style docstrings
* Include examples in docstrings
* Update relevant documentation files
* Add type hints to docstrings

.. code-block:: python

   def example_function(param1: str, param2: int = 10) -> bool:
       """Example function with proper documentation.
       
       This function demonstrates the documentation style used in phidown.
       
       Args:
           param1: Description of the first parameter
           param2: Description of the second parameter. Defaults to 10.
           
       Returns:
           True if successful, False otherwise
           
       Raises:
           ValueError: If param1 is empty
           
       Example:
           >>> result = example_function("test", 20)
           >>> print(result)
           True
       """
       if not param1:
           raise ValueError("param1 cannot be empty")
       return True

Building Documentation
^^^^^^^^^^^^^^^^^^^^^^

Build the documentation locally:

.. code-block:: bash

   cd docs
   make html
   
   # Open in browser
   open build/html/index.rst

Submitting Changes
------------------

Pull Request Process
^^^^^^^^^^^^^^^^^^^^

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure all tests pass**
4. **Update changelog** if applicable
5. **Create pull request** with descriptive title

Pull Request Template
^^^^^^^^^^^^^^^^^^^^^

Use this template for pull requests:

::

   ## Description
   Brief description of changes made.
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   - [ ] Tests added/updated
   - [ ] All tests pass
   - [ ] Manual testing completed
   
   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] Changelog updated (if applicable)

Code Review
^^^^^^^^^^^

All changes go through code review:

* Be responsive to feedback
* Make requested changes promptly
* Discuss disagreements constructively
* Keep PRs focused and small

Bug Reports
-----------

When reporting bugs:

1. **Use the issue template**
2. **Provide clear reproduction steps**
3. **Include error messages**
4. **Specify environment details**

Bug Report Template
^^^^^^^^^^^^^^^^^^^

::

   ## Bug Description
   A clear description of the bug.
   
   ## Reproduction Steps
   1. Step 1
   2. Step 2
   3. Step 3
   
   ## Expected Behavior
   What should happen.
   
   ## Actual Behavior
   What actually happens.
   
   ## Environment
   - OS: [e.g., macOS 12.0]
   - Python: [e.g., 3.11]
   - Phidown version: [e.g., 0.1.13]
   
   ## Additional Context
   Any other relevant information.

Feature Requests
----------------

For new features:

1. **Check existing issues** for similar requests
2. **Describe the use case** clearly
3. **Provide examples** of the desired functionality
4. **Consider implementation** complexity

Feature Request Template
^^^^^^^^^^^^^^^^^^^^^^^^

::

   ## Feature Description
   A clear description of the desired feature.
   
   ## Use Case
   Why is this feature needed?
   
   ## Proposed Solution
   How should this feature work?
   
   ## Alternatives
   Other approaches considered.
   
   ## Additional Context
   Any other relevant information.

Development Guidelines
----------------------

Adding New Features
^^^^^^^^^^^^^^^^^^^

1. **Design the API** first
2. **Write tests** before implementation
3. **Keep backward compatibility**
4. **Update documentation**
5. **Add examples** if applicable

Modifying Existing Code
^^^^^^^^^^^^^^^^^^^^^^^

1. **Understand the current implementation**
2. **Check for breaking changes**
3. **Update related tests**
4. **Update documentation**
5. **Consider performance implications**

Performance Considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^

* **Profile code** for bottlenecks
* **Use appropriate data structures**
* **Consider memory usage**
* **Optimize API calls**
* **Cache results** when appropriate

Security
--------

* **Never commit credentials** to the repository
* **Use secure coding practices**
* **Validate user input**
* **Handle errors gracefully**
* **Report security issues** privately

Release Process
---------------

For maintainers:

1. **Update version** in ``pyproject.toml`` and ``__init__.py``
2. **Update changelog**
3. **Create release tag**
4. **Build and upload** to PyPI
5. **Create GitHub release**

Version Numbering
^^^^^^^^^^^^^^^^^

Follow semantic versioning:

* **MAJOR**: Breaking changes
* **MINOR**: New features (backward compatible)
* **PATCH**: Bug fixes

Community
---------

* **Be respectful** and inclusive
* **Help others** in discussions
* **Share knowledge** and experiences
* **Follow the code of conduct**

Resources
---------

* `Project Repository <https://github.com/ESA-PhiLab/phidown>`_
* `Issue Tracker <https://github.com/ESA-PhiLab/phidown/issues>`_
* `Discussions <https://github.com/ESA-PhiLab/phidown/discussions>`_
* `PhiLab Website <https://philab.esa.int>`_

Thank you for contributing to Φ-Down! 🚀
