[![codecov](https://codecov.io/gh/PawelPlesniak/daqpyutils/graph/badge.svg?token=45O5BUOH3V)](https://codecov.io/gh/PawelPlesniak/daqpyutils)

[Initial plans](https://docs.google.com/document/d/1i1CPLn7UYLbrUMF2IiQNtejUSnskyRpIolfuG46PweY/edit?tab=t.0#heading=h.8u53ddxujd8q)

[Some slides from earlier](https://docs.google.com/presentation/d/1ttWGPtHcKsvJKeQOs3cHswES_xHRoXyYYxjmtbHYGT4/edit?slide=id.p#slide=id.p)

[Some more slides](https://docs.google.com/presentation/d/1Zl3YTXew__qPGyzRuToIhxjHpiGKYVDmpQsWqg0HmJk/edit?slide=id.g364767cc810_0_12#slide=id.g364767cc810_0_12)

[There are too many slides](https://docs.google.com/presentation/d/1L9yofnW52rHQCHCo0Wo1ZjJhhWegAXlxs1FH4d5BG30/edit?slide=id.p#slide=id.p)

"Parallel to daq-cmake in python"

# daqpyutils
Package for python tools, includes:
 - Package handling and creation
 - Updating package versions in preparations for a release

## How should I install this package?
This is the same as per any standard python repository, which should be installed as
```bash
pip install .
```
from the directory in which it has been cloned. For developers, do install it in editor mode with `-e`.

## Entry points
### `create_python_dunedaq_package`
Sets up a new standard python repository. Run this as
```bash
create_python_dunedaq_package <package_name> 
    -l/--log-level <logging level> 
    -c/--clean 
    -o/--overwrite 
    -r/--requirements <requirement and version number> [repeated] 
    -a/--app <app_name> [repeated]
    -p/--package-description <package description>
```
The options are as follows
 - `-l/--log-level` - sets the logging level for creating the package creation application.
 - `-c/--clean` - removes all existing files and direcotries that do not follow the standard structure.
 - `-o/--overwrite` - overwrites existing files required for the standard structure.
 - `-r/--requirements` - can specify a library requirement and optionally a version number. If a version number is not specified, this will be imported from the `venv`, and will fail if it not already in the `venv`.
 - `-a/--app <app_name>` - specifies an entry point for an application that will be available from the CLI, and creates a file that will need to be populated.
 - `-p/--package-description <package description>` - includes the package description in the `pyproject.toml`. If not present, the description will be left as a `TODO`.
 Note - the repeated fields `-r/--requirements` and `-a/--app` can be used multiple times, e.g. as `create_python_dunedaq_package <package_name> -r click -r rich==13.9.4`

## Usage of standard developer tools
A set of standard developer tools have been included in the standard `optional-depenmdencies` and `pre-commit` config. These are:

### `pyproject.toml`
Defines the build structure and code standard checking configuration. For a detail of which linting tools and formatting tools have been used, see the `daqpyutils` `pyproject.toml` (NB. this requires a link).

### `ruff`
This is a linter that applies a selection of rules to 

### `pre-commit`
The use `pre-commit` is intended for developer use only. When installing the package that you are developing, perform the following steps
```
pip install -e .[dev]
pre-commit clean
pre-commit install
```
When you are using `git commit`, the `isort`, `ruff`, and `black` tools will be run. 

## Diagram guidance

### Drawing with `draw.io`
Box diagrams help with digesting the contents of a repository, so the development of these diagrams has been integrated to make it as simple as possible. For `VSCode` or other graphical IDE users,
 - Download the `draw.io integration` or `draw.io for VSCode` extension.
 - Create a diagram in the `<repo_root>/diagrams/` directory
 - Open the file - this should automatically open the file in the `draw.io` interpreter

### Drawing with `mermaid`
Mermaid allows to draw diagrams with markdown. This includes UML, sequence, flowcharts, amongst others. An example is provided in `<daqpyutils_root>/diagrams/example.md`. This does not require compilation and allows for a diagram in the documentation to be updated without generating files, just be editing code. For `VSCode` or other graphical IDE users,
 - Download the `Mermaid` extension
 - When scripting your diagram, you can view the progress and validate correct syntax by previewing the diagram before committing.

## Commonly encountered problems with pre-commit
### `[INFO] Initializing environment for ...`
This is due to a lack of internet connection, typically encountered on the `np0X` servers. Enable your web proxy with `source ~np04daq/bin/web_proxy.sh`, run the check, and unset your proxy when it runs successfully with `source ~np04daq/bin/web_proxy.sh -u`.

### `error: pathspec 'v6.0.1' did not match any file(s) known to git`
This is due to an incorrect package version in your `pre-commit` venv. To fix this run `pre-commit autoupdate`. This will check the software versions in your venv and update your `.pre-commit-config.yaml` to include the newest versions.
