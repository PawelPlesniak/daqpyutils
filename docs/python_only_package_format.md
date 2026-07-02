# Packaging formats
In order to simplify the installation and maintenance approach of the python-only packages that form part of the DUNE-DAQ release areas, the following structure is used
```
<package_name>
├── .git/
│   └── standard git directory structure
├── .github/
│   └── ISSUE_TEMPLATE/
│   └── workflows/
│       └── lint.yml
│       └── run_pytest.yml
│       └── track_new_issues.yml
│       └── track_new_prs.yml
│   └── pull_request_template.md
├── docs
│   └── README.md
├── scripts/
├── src/
│   └── <package_name>/
│       ├── apps/
│       │   └── __init__.py (empty)
│       ├── integtest/
│       └── __init__.py (empty)
├── tests/
├── .gitignore
├── .pre_commit_config.yml
└── pyproject.toml
```

In the following sections, the motivation and use cases of each subdirectory will be defined in order of the tree structure

## `.git`

Allows for repository maintenance in GitHub. The user is not expected to develop anything in this repo, this is managed by the CLI/GUI interfaces to `git` commands.

## `.github`

Allows for the standard definition location of tools that are used to support a GitHub based deployment model. It contains the definitions of issue templates, which are templates that are used by the organization for standardized definitions of issue structures, centralizing management of the development lifecycle by defining metadata allowing tracking of development progress, and planning for release cycles. The standard issue templates are defined and managed by the Software Co-ordination team, which is defined [here](https://github.com/DUNE-DAQ/.github/tree/develop/issue-templates).

This path also defines both standard and repository specific CI/CD workflows. These are actions that can be run on the GitHub nodes to run automated checks prior to merging a pull request. In the template defined above, the following workflows are defined and managed [here](https://github.com/DUNE-DAQ/.github/tree/develop/workflow-templates) DUNE DAQ organization
 - `run_pytest.yml` - runs the unit tests defined in the `tests/` path.
 - `track_new_issues.yml` - assigns new issues to the DUNE DAQ [project board](https://github.com/orgs/DUNE-DAQ/projects/5).
 - `track_new_prs.yml` - assigns new PRs to the DUNE DAQ [project board](https://github.com/orgs/DUNE-DAQ/projects/5).

The only workflow that is specified directly for Python-only repositories is the following
 - `lint.yml` - runs automatic linting tools. For python-only repositories, this will be run using `ruff`.
 - `check_links.yml` - checks the links used in documentation pages to ensure they are valid.
 - `check_dirs_init_file.yml` - checks the required paths (everything in `<project_name>/src/<project_name>` has an `__init__.py` file, outside of the `integtest/` path).

 The last part of this directory is `pull_request_template.md`, which defines a template for pull requests. The base template is defined and managed by te Software Co-ordination team, and is defined [here](https://github.com/DUNE-DAQ/.github/blob/develop/pull-request-templates/pull_request_template.md). The templates defined in each repository are recommended to be tailored to each individual use case, as is defined [here](https://github.com/DUNE-DAQ/.github/tree/develop/pull-request-templates). Using [`drunc`](https://github.com/DUNE-DAQ/drunc) as an example, as this is a tool that is used by all developers, a detailed explanation of the changes made in a PR is recommended to be written by the developer, to enable rapid debugging in the case of a recent change affecting the global system. This custom PR template is defined [here](https://github.com/DUNE-DAQ/drunc/blob/develop/.github/pull_request_template.md), and is also available [here](https://github.com/DUNE-DAQ/.github/blob/develop/pull-request-templates/drunc/pull_request_template.md).
 <!-- TODO: Ask John about this format and purpose -->

## `docs`

This is the standard location for the documentation markdown files, aimed at the user not the developer. The exact details on the structure and use cases splitting the documentation location for users and developers is defined [here](https://dune-daq-sw.readthedocs.io/en/latest/editing_package_documentation/), and is not expanded on in this text to reduce the maintenance load.

## `scripts`

The standard use case for this directory is documented [here](https://dune-daq-sw.readthedocs.io/en/latest/packages/daq-cmake). This is the location for scripts that we want a user to have access to only in the case that they have a local copy of the repository and need to use the scripts to make changes to the repository. In deployment terms, this means that the script is not defined as an terminal entry point, and is only accessible if executed manually. This is a logical boundary, restricting access to the script to cases in which it is required.

As an example, in [`druncschema`](https://github.com/DUNE-DAQ/druncschema), a general user is not expected to recompile the schemas using the [compilation script](https://github.com/DUNE-DAQ/druncschema/blob/develop/scripts/generate_protos.py). This action is only necessary on changes of the schema, which require a local copy of the repository.

Any other scripts that the user should have access to when a package is installed should be defined as an `entry-point`, which is defined below in the description of the structure of the `pyproject.toml`.

## `src`

This is where the source code of the package lives. The second scoping of the package name is required for defining the physical representation of the code that users will import. In the example of `daqpyutils` (this repository), it means that if any imports are required, the package scopes the name of the import, i.e. to import `repository_handling/defaults`, this will be imported as
```python
from daqpyutils.repository_handling.defaults import default_subdirs
```
which allows for package-name scoping resolution for `import`. It also allows for the separation of the project source code, which is required to operate the package, as well as to compartmentalise the extra code that does not form part of the library, such as the documentation and unit tests. It also means that when packaging the repository using wheels or tarballs, we do not need to ship the parts of the non-library contents.

Within the project `<project_name>/src/<project_name>` path, there is a `__init__.py` file which is a signature that tells the Python interpreter to treat the repository as a package, allowing for the dot scoped import notation (e.g. `from daqpytools.repository_handling.defaults import ...`). This can also be used to change the hierarchical location of modules for external package importing. This file can optionally be used to set up global package variables, which may be useful e.g. with pseudo-root `logger` instantiation, as per the [`daqpytools`](https://github.com/DUNE-DAQ/daqpytools) [documentation](https://dune-daq-sw.readthedocs.io/en/latest/packages/daqpytools/how-to/best-practices/#ers-implementation).

The `integtest` path within the repository is an exception that does not require an `__init__.py` file, as this code is not intended to be importable outside of the scope. The location of this folder is an intentional design to allow the python-only repository integration tests to be ran without requiring a locally installed copy of the repository, to align with the requirements of the global CD workflows. This design allows the organization to include integration tests within the nightly and candidate releases, and to remove them from stable releases.

## `tests`

This is the location of the unit tests written for the repository. The standard workflow operates using `pytest`, and it is recommended that the path structure is similar to that of the source code path (excluding the extra scoped package name path) following standard Python practices. The configuration for `pytest`s is defined in the `pyproject.toml`, in the `[tool.pytest.ini_options]` options. By default, the tests are configured to use the following options

### Command-Line Options
 - `--cov=<package_name>`: Enables coverage measurement, tracking how much of that specific source code is executed during the test run.
 - `--cov-report=html`: Configures the format and output location of the coverage report.
 - `--doctest-modules`: Tells pytest to scan all python modules for docstrings containing code examples and execute them as tests to ensure documentation stays accurate.
 - `--ignore=docs/`: Instructs pytest to completely skip the `docs/` directory during test collection, which avoids parsing irrelevant and potentially large files and paths.


### Configuration Settings
 - `norecursedirs`: A list of directory patterns that pytest should avoid recursing into entirely. This is more global than `--ignore` and helps speed up test collection by preventing the crawler from entering large or irrelevant directories. This is configured to skip reading the paths `.git/`, `.github/`, and `.venv`.
 - `testpaths`: A list of directory paths that pytest should exclusively search for tests. This is configured to only read the `tests/` path.

Note - the `mypy` checks are also defined in the `pytest` options, but are defined in the `pyproject.toml` section below.

## `.gitignore`
This is the list of standard excludes for DUNE DAQ packages from git versioning. This is the same as is used by the C++ packages, for globally standard maintenance. Any additions required for a particular packages should be added at the top of the file for clarity.

## `.pre_commit_config.yml`
Contains the set of standard checks to run when executing `git commit`. This is currently configured to run the `ruff` linter, with the unit testing deferred to the CI workflows for convenience during running. The linting rules are set up in the `pyproject.toml`, thus are defined there too. Unlike other external tools, the configuration for `pre-commit` cannot natively be specified in the `pyproject.toml` as it is a language agnostic framework.

## `pyproject.toml`
This file defines the blueprint of how the package is intended to be build, what it requires in various installation modes, entry points, and standard tooling configuration. Each of these topics will be defined individually as follows.

Notes for the developer 
 - Should any changes be made in the `pyproject.toml`, a fresh `pip install` will be required to implement the changes.
 - It is recommended that when developing, the edit mode is used as `pip install -e <path_to_project_root>`

### Project specification and installation 
The current building tooling and versioning requirement is defined in `[build-system]`, which is configured to use `setuptools`. This is not expected to change on a per repository basis, and proposed changes with their justification should be discussed at a SWIT meeting. The developer is not expected to change these parameters. The other build system parameters specified are
 - `[tool.setuptools.packages.find]` - location of the project source code, not expected to change.
 - `[project.setuptools.package-data]` - location of project data files that should be placed inside the project structure. Commonly used examples are `html`, `json`, and `.pyi` files. This is required as otherwise these files are not packaged with the environment when using a virtual environment deployment.


The project that the repository implements has metadata defined in the `[project]` section, and project configuration parameters specified in dot scoped blocks. The base `[project]` specification including the following parameters
 - `name` - the name of the repository, expected to be static.
 - `description` - a description of the role of the repository, expected to be static.
 - `version` - the version number, which changes following the release schedule.
 - `readme` - the path to the base `README.md`, which provides a high-level overview of the usage of the repository, expected to be static.
 - `requires-python` - python version required to use this repository, expected to be static. As per the `[build-system]`. the python version is only excpected to change globally and not on a per-repository case.
 - `dependencies` - the list of packages required to use the repository source code.

The `project` may also specify optional dependencies, which are those tailored to the use case and do not form part of the source code dependencies. The common optional dependency groups and their dependencies included in the template include
 - `dev` - the additional packages a developer will commonly need, has packages:
   - `pytest` - runs unit/integration tests.
   - `pytest-cov` - calculates the coverage of the unit tests.
   - `ruff` - linting configuration (see later in this section).
   - `pre-commit` - defines a hook to execute the linting on `git commit`.
 - `test` - the additional packages a testing environment will commonly need, has packages:
   - `pytest`
   - `pytest-cov`
These optional installation modes can then be used as a suffix to the installation location as
```python
pip install <path_to_project_root>[mode]
```

The last component that is specified in `project` are the CLI entry points which are accessible if the package has been installed in the virtual environment, regardless of the source code location. These are specified in the `[project.scripts]` block, which typically point to individual applications living in the `<package_name>/src/<package_name>/apps/` path. 

### External tool configurations

Outside of specifying the installation tool and the project structure, the `pyproject.toml` also contains the configuration of external tools that are used within the repository. The default ones specified in the template are defined as follows

#### Ruff 
Ruff is an extremely fast Python linter and code formatter, designed as a modern, high-performance replacement for older tools like `Flake8`, `isort`, and `Black`. The `google` documentation docstring convention has been chosen for its readability with both IDEs and terminals, as well as using clear sections for argument, return type, and raise descriptors to give the reader an easy and quick understanding of the purpose of the code. The default implementation of `ruff` has the following linting rules

Rules:
 - `D` - `pydocstyle`: check for docstring conventions
 - `E` - `pycodestyle` errors: standard PEP 8 errors
 - `F` - `Pyflakes`: check for common programming errors
 - `I` - `isort`: best practices for import order and sorting
 - `UP` - `pyupgrade`: suggestions for code modernization
 - `RUF` - Ruff-specific rules: built-in Ruff-specific warnings
 - `ANN` - `flake8-annotations`: check for missing type annotations

Ignore rules:
 - `D205` - Documentation Existence - Every module needs a summary.
 - `D100` - Documentation Existence - Every package needs a summary.
 - `D104` - Documentation Formatting - Separate the summary from details.

There are also specific rules implemented for the unit tests, these are defined in the `[tool.ruff.lint.per-file-ignores]` section. The default rules in the template include those in the ignore rules section above, and are extended to include
 - `S101` - allows for `assert`s in the tests
 - `ANN201` - allows for missing return types

## Strict mode and `mypy`
For most development in python, the implementation defined above is sufficient for safe development practices. However, for applications that are used very commonly, it is worth considering using the `--strict` operator to create the package. This introduces `mypy`, which is a signature checking tool that validates types used in function signatures and calls. In strict mode, the `mypy` tool is configured to use the following rules
 - Function and Definition Strictness
    - `disallow_untyped_defs = true` -  Force all functions to have type annotations for arguments and return values.
    - `disallow_incomplete_defs = true` -  Disallow functions that have some, but not all, arguments annotated.
    - `check_untyped_defs = true` -  Type-check the body of functions even if they lack type annotations.
    - `no_implicit_optional = true` -  Force 'Optional[T]' instead of just 'T' when a default value is None.
 - Warning and Code
    - `warn_return_any = true` -  Warn when a function returns 'Any' where a more specific type was expected.
    - `warn_unused_ignores = true` -  Warn if you have a '# type: ignore' comment that isn't actually silencing an error.
    - `warn_redundant_casts = true` -  Warn when a 'cast()' is used but the expression already has that type.
    - `strict_equality = true` -  Disallow comparing types that are not compatible (e.g., comparing int to None).
 - Controlling the 'Any` -  Type
    - `disallow_any_generics = true` -  Disallow usage of generic types (like List, Dict) without specific parameters.
    - `disallow_subclassing_any = true` -  Disallow inheriting from a class that is typed as 'Any'.
    - `disallow_any_explicit = true` -  Disallow explicit usage of the 'Any' type in your code.
    - `disallow_any_expr = false` -  Allow 'Any' in expressions; often kept false to avoid overwhelming errors in legacy code.
    - `disallow_any_decorated = true` -  Disallow 'Any' in functions that are decorated.
    - `disallow_any_unimported = true` -  Disallow 'Any' from types that aren't imported properly.
 - Configuration and Reporting
    - `warn_unused_configs = true` -  Warn if a section in your config file is never used (helps catch typos).
    - `show_error_codes = true` -  Show the specific code (e.g., [arg-type]) for every error to make filtering easier.

If strict mode is used, the following additional rules are also implemented
 - The `pytest-mypy` options are added to the `pytest` configuration.
 - The line length is restricted to 88 characters.
 - The following `ruff` linting rules are also put in place
    - `S` - `flake8-bandit`: check for common security issues
    - `N` - `pep8-naming`: check for PEP 8 naming conventions
    - `ERA` - `eradicate`: find and remove commented-out code
    - `B` - `flake8-bugbear`: find likely bugs and design problems
    - `C4` - `flake8-comprehensions`: improve list/dict/set comprehensions
    - `A` - `flake8-builtins`: check for shadowing of Python built-in symbols
    - `RET` - `flake8-return`: check for unnecessary return statements
    - `ISC` - `flake8-implicit-str-concat`: detect implicit string concatenation
    - `G` - `flake8-logging-format`: ensure proper logging format strings
    - `TRY` - `tryceratops`: prevent abuse of try/except blocks
    - `T` - `flake8-debugger`: catch tracepoints or debugger calls

Note that these rules are heavily restrictive, and it is left to the developer to decide which of these rules are relevant to the development model of the new application.