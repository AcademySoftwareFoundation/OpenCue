# Building Python APIs reference docs

This guide explains how to set up your development environment to build the
HTML reference docs for the various Python packages and modules in OpenCue. The
project is also working on publishing the generated API reference docs on
www.opencue.io, but in the meantime you can build the reference HTML locally.
This guide is also useful if you want to build the HTML reference during
development.

Currently, OpenCue supports building HTML reference docs for the `outline`
package. The `outline` package is the primary package for submitting and
managing jobs in OpenCue. We'll add support for building additional
packages soon.

## Before you begin

You must have the following software installed on your machine:

*   Python version 2.7 or greater
*   The Python `pip` command
*   The Python `virtualenv` tool

If you don't already have a recent local copy of the OpenCue source code, you
must do one of the following:

1.  Download and unzip the
    [OpenCue source code ZIP file](https://github.com/AcademySoftwareFoundation/OpenCue/archive/master.zip).

2.  If you have the `git` command installed on your machine, you can clone
    the repository:

    ```
    git clone https://github.com/AcademySoftwareFoundation/OpenCue.git
    ```

## Building and view the reference docs

To build and view the HTML reference docs:

1.  Create a Python virtual environment:

    ```
    virtualenv venv
    source venv/bin/activate
    ```

1.  Install Sphinx:

    ```
    pip install sphinx sphinx-theme
    ```

1.  Install all other dependencies:

    ```
    pip install -r requirements.txt
    ```

1.  Compile the OpenCue Cuebot protos, as these are dependencies for the
    Python packages:

    ```
    cd proto
    python -m grpc_tools.protoc -I=. --python_out=../pycue/opencue/compiled_proto --grpc_python_out=../pycue/opencue/compiled_proto ./*.proto
    cd ..
    ```

1.  Change to the `docs` directory:

    ```
    cd ../docs
    ```

1.  Build the docs:

    ```
    make html
    ```

1.  To view the HTML output from Sphinx, open the following HTML file in a
    browser:

    Note: Currently, Sphinx is only configured to generate HTML docs for the
    `outline` package.

    ```
    <path-to-OpenCue>/OpenCue/docs/_build/html/index.html
    ```

## Customizing the theme

To customize the theme for the generated docs:

1.  Open `docs/conf.py` for editing.

1.  Comment the following line:

    ```
    html_theme = 'alabaster'
    ```

1.  Add the followin code, replacing '<name-of-the-theme>' with a theme:

    Note: You can browse available themes at https://sphinx-themes.org/.

    ```
    html_theme = '<name-of-the-theme>'
    import sphinx_theme
    html_theme_path = [sphinx_theme.get_html_theme_path()]
    ```

1.  Rebuild the docs:

    ```
    make clean
    make html
    ```

## Submitting changes to the docs

Before you commit and submit changes as a pull request, remove any generated
HTML output:

```
make clean
```