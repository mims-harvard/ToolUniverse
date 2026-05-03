.. _deployment:

Documentation Deployment
========================

Quick Start
-----------

Build and serve documentation locally:

.. code-block:: bash

   cd docs/
   ./build_docs.sh
   ./validate_docs.sh

The validation script will offer to start a local server at http://localhost:8080.

GitHub Pages
------------

Automated Deployment
~~~~~~~~~~~~~~~~~~~~

The repository includes GitHub Actions workflow for automatic deployment to GitHub Pages.

**Setup Steps:**

1. Enable GitHub Pages in repository settings:
==============================================
   - Go to repository **Settings > Pages**
   - Set source to **GitHub Actions**

2. Push to main branch - documentation will build automatically

3. Access documentation at: ``https://yourusername.github.io/ToolUniverse/``

Manual Deployment
~~~~~~~~~~~~~~~~~

For manual GitHub Pages deployment:

.. code-block:: bash

   # Build documentation
   cd docs/
   ./build_docs.sh

   # Copy to gh-pages branch
   git checkout --orphan gh-pages
   git rm -rf .
   cp -r docs/_build/html/* .
   git add .
   git commit -m "Deploy documentation"
   git push -f origin gh-pages

ReadTheDocs
-----------

Automated Setup
~~~~~~~~~~~~~~~

1. Connect repository to ReadTheDocs:
=====================================
   - Visit https://readthedocs.org/
   - Import repository
   - Configure webhook (automatic)

2. Configuration file ``.readthedocs.yaml`` is already provided

3. Documentation builds automatically on commits

Configuration
~~~~~~~~~~~~~

The ``.readthedocs.yaml`` file specifies:

- **Python version**: 3.8+
- **Requirements**: ``docs/requirements.txt``
- **Sphinx configuration**: ``docs/conf.py``
- **Output formats**: HTML, PDF

Local Development Server
------------------------

Development with Auto-reload
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use sphinx-autobuild for live reloading during development:

.. code-block:: bash

   # Install if not already installed
   pip install sphinx-autobuild

   # Start development server
   cd docs/
   sphinx-autobuild . _build/html --port 8080

The server will automatically rebuild when files change.

Production Server
~~~~~~~~~~~~~~~~~

For production hosting, use a proper web server:

**Nginx example:**

.. code-block:: nginx

   server {
       listen 80;
       server_name docs.yourdomain.com;
       root /path/to/ToolUniverse/docs/_build/html;
       index index.html;

       location / {
           try_files $uri $uri/ =404;
       }
   }

**Apache example:**

.. code-block:: apache

   <VirtualHost *:80>
       ServerName docs.yourdomain.com
       DocumentRoot /path/to/ToolUniverse/docs/_build/html
       DirectoryIndex index.html
   </VirtualHost>

Docker Deployment
-----------------

Dockerfile for Nginx
~~~~~~~~~~~~~~~~~~~~~

Create ``Dockerfile`` in docs directory:

.. code-block:: dockerfile

   FROM nginx:alpine
   COPY _build/html /usr/share/nginx/html
   EXPOSE 80

Build and run:

.. code-block:: bash

   cd docs/
   ./build_docs.sh
   docker build -t tooluniverse-docs .
   docker run -p 8080:80 tooluniverse-docs

Multi-stage Build
~~~~~~~~~~~~~~~~~

For smaller images with build included:

.. code-block:: dockerfile

   # Build stage
   FROM python:3.9-slim as builder
   WORKDIR /docs
   COPY . .
   RUN pip install -r requirements.txt && \
       sphinx-build -b html . _build/html

   # Serve stage
   FROM nginx:alpine
   COPY --from=builder /docs/_build/html /usr/share/nginx/html
   EXPOSE 80

Continuous Integration
----------------------

GitHub Actions
~~~~~~~~~~~~~~

The ``.github/workflows/docs.yml`` workflow:

- **Triggers**: Push to main, pull requests
- **Builds**: HTML and PDF documentation
- **Deploys**: To GitHub Pages (on main branch)
- **Tests**: Link checking, validation

View workflow status in repository **Actions** tab.

Custom CI/CD
~~~~~~~~~~~~

For other CI systems, use these commands:

.. code-block:: bash

   # Install dependencies
   pip install -r docs/requirements.txt

   # Build documentation
   cd docs/
   sphinx-build -b html . _build/html

   # Validate build
   ./validate_docs.sh

   # Deploy (custom logic)
   ./deploy.sh

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Build fails with module import errors:**

.. code-block:: bash

   # Install project in editable mode
   pip install -e .
   cd docs/
   ./build_docs.sh

**Missing static files:**

.. code-block:: bash

   # Clean and rebuild
   cd docs/
   make clean
   ./build_docs.sh

**Broken links:**

.. code-block:: bash

   # Check with sphinx-build
   sphinx-build -b linkcheck . _build/linkcheck

**Permission errors on deployment:**

.. code-block:: bash

   # Fix file permissions
   chmod +x docs/*.sh

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

For large documentation sites:

1. **Enable parallel builds:**

   .. code-block:: python

      # In conf.py
      numjobs = 4  # Use multiple processes

2. **Optimize images:**

   .. code-block:: bash

      # Compress images in _static/
      find _static/ -name "*.png" -exec optipng {} \;

3. **Use CDN for static files:**

   .. code-block:: python

      # In conf.py
      html_baseurl = 'https://cdn.yourdomain.com/'

Monitoring
----------

Health Checks
~~~~~~~~~~~~~

Create a simple health check endpoint:

.. code-block:: bash

   # Check if documentation is accessible
   curl -f https://yourdocs.com/ || exit 1

Analytics
~~~~~~~~~

Add Google Analytics to ``conf.py``:

.. code-block:: python

   html_theme_options = {
       'analytics_id': 'UA-XXXXXXX-1',
   }

Or add custom tracking code to ``_templates/layout.html``.

Backup and Recovery
-------------------

Backup Strategy
~~~~~~~~~~~~~~~

1. **Source control**: Documentation source in Git
2. **Built artifacts**: Archive built documentation
3. **Dependencies**: Pin versions in requirements.txt

.. code-block:: bash

   # Create backup
   tar -czf docs-backup-$(date +%Y%m%d).tar.gz _build/

Recovery
~~~~~~~~

.. code-block:: bash

   # Restore from backup
   tar -xzf docs-backup-20231201.tar.gz

   # Or rebuild from source
   ./build_docs.sh

This completes the deployment configuration. The documentation system now supports multiple deployment targets with automated CI/CD integration.
