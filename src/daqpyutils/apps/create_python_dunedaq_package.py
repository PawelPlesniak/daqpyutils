import re
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import click
from daqpytools.logging.levels import logging_log_level_to_int, logging_log_level_keys
from daqpytools.logging.logger import get_daq_logger
from git import Repo
from jinja2 import Template

from daqpyutils.repository_handling.defaults import default_subdirs

template_path = Path(__file__).parent.parent / "templates"
log = get_daq_logger(logger_name="create_python_dunedaq_package", rich_handler=True)
template_variables: dict[str, str | bool] = {}

def validate_package(package_name: str) -> bool:
    """
    Validate that the package is installed in the current environment.
    If not found locally, checks if it exists on PyPI.

    Args:
        package_name: The name of the package to validate.

    Returns:
        bool: True if the package is found locally or on PyPI,.

    Raises:
        SystemExit: If the package is not found locally or on PyPI.
    """
    # 1. Check local environment first (fast)
    try:
        version(package_name)
        log.debug("Package '%s' found in local environment.", package_name)
        return True
    except PackageNotFoundError:
        log.debug("Package '%s' not found locally, checking PyPI...", package_name)

    # 2. Check PyPI (slower, requires network)
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            log.info("Package '%s' exists on PyPI.", package_name)
            return True
    except requests.RequestException as e:
        log.exception("Requested package %s was not found in either the virtual environment or in PyPI, exiting.%s", package_name, e)
        sys.exit(1)

def unpack_items(
    items: tuple[str, str|int] | list[str] | str | None = None,
    items_file: str | None = None,
) -> list[str]:
    """
    Ensure the input is returned as a list of strings.

    The file is expected to contain one item per line, with comments starting with # and
    empty lines ignored. This will parse the contents of file intended to populate 
    the requirements or applications list. 

    For an example of parsing applications list, the items_file should look like:
        # This is a comment
        app1
        app2
        # Another comment
        app3
    
    For an example of parsing requirements list, the items_file should look like:
        # This is a comment
        package1==1.0.0
        package2
        # Another comment
        package3==2.1.0

    Note - following the current virtual environment deployment model for releases, the
    version numbers associated with each package will be removed, instead using packages
    already included in the virtual environment, or allowing pip to determine a version
    compatible with the other packages in the environment.
    
    Example usage:
    >>> unpack_items(items=("package1==1.0.0", "package2"), items_file=None)
    ['package1', 'package2']

    Args:
        items: A tuple, list, or string of items to unpack.
        items_file: A file containing a list of items to unpack.

    Returns:
        A list of strings containing the unpacked items.

    Raises:
        SystemExit: If the input is invalid or if the items file does not exist.
    """

    # Construct the return variable
    ret: list[str] = []

    # Sanity check
    if not items and not items_file:
        return ret

    # Unpack the items based on their type
    if isinstance(items, list):
        ret.extend(items)
    if isinstance(items, str):
        ret.append(items)
    if items_file:
        log.info("Commencing parsing the contents of %s to list", items_file)

        # Validate that the file exists
        items_path = Path(items_file)
        if not items_path.is_file():
            log.error("%s is not a file or does not exist, exiting.", items_file)
            sys.exit(1)

        # Parse the file and format the relevant lines into a list of strings, inferring
        # their use based on their format, and ignoring both comments and empty lines
        with items_path.open("r") as f:
            for line in f:
                line = line.strip()
                log.debug("Parsing %s", line)
                # Ignore empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Enforce that the line is a valid package name or package name with version number
                if re.match(r"^[a-zA-Z0-9_-]+(==\d+\.\d+\.\d+)?$", line):
                    log.warning(
                        "%s is recognised as a package with a version number, removing "
                        "the version number for compatibility with the virtual "
                        "environment.",
                        line
                    )
                    package_name = line.split("==")[0]
                    validate_package(package_name)
                    ret.append(package_name)
                elif "=" in line:
                    log.debug(
                        "Received string %s, not formatting it assuming that it is a "
                        "project script.",
                        line,
                    )
                    ret.append(line)
                else:
                    log.info(
                        "Received string %s, assuming that it is a package name without "
                        "a version number.",
                        line,
                    )
                    validate_package(line)
                    ret.append(line)

                items_list.append(line)
        return items_list


def validate_compliance_with_naming_conventions(package_name: str, applications: list[str]) -> None:
    """Validate the package names."""
    if package_name == ".":
        log.error(
            "You passed '.' as the name of the package. Perhaps you meant to use the "
            "tool validate_python_dunedaq_package_structure?"
        )
        sys.exit(1)
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9]*", package_name):
        log.error(
            "The package name [red]%s[/red] doesn't satisfy the requirement that the "
            "package begin with a lowercase letter and consist only of letters and "
            "numbers.",
            package_name,
        )
        sys.exit(1)
    for application in applications:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", application):
            log.error(
                "Requested user application name %s needs to be in kebab-case. Please "
                "see https://dune-daq-sw.readthedocs.io/en/latest/packages/styleguide/ "
                "for more on naming conventions.",
                application,
            )
            sys.exit(1)
    return


def setup_dot_git(package_path: Path) -> None:
    """Sets up .git/ dir.
    If it already exists, checks if it is correctly structured.
    If it doesn't exist, it gets written.
    """
    log.info("Setting up the .git repository.")
    Repo.init(package_path, mkdir=True)
    return


def make_subdirs(package_path: Path, applications: list[str]) -> None:
    """Make the subdirectories."""
    setup_dot_git(package_path)
    package_name = package_path.name
    create_subdirs = [package_path / subdir for subdir in default_subdirs]
    create_subdirs.append(package_path / "src" / package_name)
    if applications:
        create_subdirs.append(package_path / "src" / package_name / "apps")
    for subdir in create_subdirs:
        if not subdir.exists():
            log.info("Generating directory %s", subdir)
            subdir.mkdir(parents=True)
    return


def populate_template(
    template_file_path: Path, template_variables: dict[str, Any], output_path: Path
) -> None:
    """Populate a template with its variables and save the output render."""
    template = Template(template_file_path.read_text())
    result = template.render(**template_variables)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log.debug("Populating template [green]%s[/green]", template_file_path.name)
    with open(output_path, "w") as output_file:
        output_file.write(result)
    log.info(
        "File [green]%s[/green] written to [purple]%s[/purple].",
        output_path.name,
        output_path,
    )
    return


def copy_template(file_name: Path | str, output_path: Path) -> None:
    """Copy a template file to the output path."""
    template_file_path = template_path / file_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log.debug("Copying template [green]%s[/green]", file_name)
    shutil.copy(template_file_path, output_path)
    log.info(
        "File [green]%s[/green] written to [purple]%s[/purple].",
        output_path.name,
        output_path,
    )
    return


def construct_default_readme_md(package_path: Path, description: str) -> None:
    """Construct the default docs/README.md with the package name and description."""
    output_file = package_path / "docs" / "README.md"
    template_variables = {"PACKAGE_NAME": package_path.name, "DESCRIPTION": description}
    populate_template(template_path / "readme.jinja", template_variables, output_file)
    return


def construct_default_gitignore(package_path: Path) -> None:
    """Construct the default .gitignore with the default ignore dirs and files."""
    copy_template("gitignore.jinja", package_path / ".gitignore")
    return


def construct_default_dot_github(package_path: Path) -> None:
    """Construct the default .github/workflows/*.yml with the default CI workflows."""
    template_workflow_dir = template_path / "github"
    workflow_files = [
        template_workflow_dir / file.name
        for file in template_workflow_dir.iterdir()
        if file.is_file()
    ]
    destination = package_path / ".github"
    for file in workflow_files:
        copy_template(file, destination / file.name)

    template_workflow_dir = template_workflow_dir / "workflows"
    workflow_files = [
        template_workflow_dir / file.name
        for file in template_workflow_dir.iterdir()
        if file.is_file()
    ]
    destination = package_path / ".github/workflows"
    for file in workflow_files:
        copy_template(file, destination / file.name)

    log.info("GitHub workflows copied to %s", destination)
    return


def construct_default_pre_commit_config_yaml(package_path: Path) -> None:
    """Construct the default .pre-commit-config.yaml with all pre-commit actions."""
    copy_template("pre-commit-config.jinja", package_path / ".pre-commit-config.yaml")
    return


def construct_application_file(application: str, application_path: Path) -> None:
    """Construct default application file for given <application>."""
    template_variables = {"APPLICATION": application}
    populate_template(
        template_path / "application.jinja", template_variables, application_path
    )
    return


def parse_applications(package_path: Path, applications: list[str]) -> str:
    """Construct default entry points for pyproject.toml and application files."""
    template_entry_points = "[project.scripts]"
    package_name = package_path.name
    for application in applications:
        application_path = f"{package_name}/apps/__main_{application}__"
        construct_application_file(
            application, package_path / "src" / (application_path + ".py")
        )
        application_entry_point = application_path.replace("/", ".") + ":main"
        template_entry_points += f"\n{application} = {application_entry_point}"
        log.info("Added application %s to pyproject.toml", application)

    return template_entry_points


def format_requirements(requirements: list[str]) -> list[str]:
    """Format the requirements for use in pyproject.toml.
    Requirements passed as either of:
    * "package_name==X.Y.Z"
    * "package_name"
    Search the venv for each package. If version not specified, use available version.
    If version specified and matches available, use it. If package not available, throw.
    """
    formatted_requirements = []
    requirement_pattern_with_version = r"^[a-zA-Z0-9_-]+==\d+\.\d+\.\d+$"
    requirement_pattern_without_version = r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$"
    log.debug("Processing requirements: %s", requirements)
    for requirement in requirements:
        if bool(re.match(requirement_pattern_with_version, requirement)):
            package_name, requested_package_version = requirement.split("==")
        elif bool(re.match(requirement_pattern_without_version, requirement)):
            package_name = requirement
            requested_package_version = ""
        else:
            log.error(
                "Requirement %s improperly formatted, expected a package name or a "
                "package name with version number, e.g. <package_name==X.Y.Z>.",
                requirement,
            )
            sys.exit(1)

        try:
            available_package_version = version(package_name)
            if available_package_version == requested_package_version:
                log.debug(
                    "%s found with version %s", requirement, available_package_version
                )
                formatted_requirements.append(requirement)
            else:
                log.info(
                    "Package %s requested with version %s, but found installed version "
                    "%s. Using this version.",
                    package_name,
                    requested_package_version,
                    available_package_version,
                )
                formatted_requirements.append(
                    f"{package_name}=={available_package_version}"
                )
        except PackageNotFoundError:
            log.exception(
                "Package %s not found in environment, skipping.", package_name
            )
            sys.exit(1)
    return formatted_requirements


def construct_default_pyproject_toml(
    package_path: Path,
    package_description: str,
    requirements: list[str],
    applications: list[str],
    strict: bool,
) -> None:
    """Construct pyproject.toml in repository root."""
    output_file = package_path / "pyproject.toml"
    package_name = package_path.name

    template_variables: dict[str, str | bool] = {
        "PACKAGE_NAME": package_name,
        "DESCRIPTION": package_description,
    }

    if applications:
        template_variables["APPLICATIONS"] = parse_applications(
            package_path, applications
        )
        log.info("Added all script entry points")

    if requirements:
        requirements = format_requirements(list(requirements))
        requirements_str = "\n".join(f'\t"{pkg}",' for pkg in requirements) + "\n"
        template_variables["DEPENDENCIES"] = requirements_str

    template_variables["STRICT"] = bool(strict)

    populate_template(
        template_path / "pyproject.jinja", template_variables, output_file
    )
    return


def construct_inits(package_path: Path) -> None:
    """Construct empty __init__.py files in all subdirs of src/{package_name}."""
    directories = [
        d for d in (package_path / "src" / package_path.name).rglob("*") if d.is_dir()
    ]
    for directory in directories:
        file = directory / "__init__.py"
        file.touch()
    return


def summary_logging(package_name: str, needs_description: bool) -> None:
    """
    Summarize the package creation, and the remaining tasks required to integrate the 
    package with the DUNE-DAQ github oragnization.
    
    >>> summary_logging("my_package", True)
    [green]You have successfully created your package my_package[/green]. To publish it, you need to:
        Assign an appropriate [bold green]version number[/bold green] in the pyproject.toml
        [bold green]'git push`[/bold green] to remote in your private github
        Create a pull request for your changes.
        Set up your pytest-cov key.
        Add a [bold green]package description[/bold green] in the pyproject.toml
        Get in touch with John Freeman and Andrew Mogan for review before they include it in the DUNEDAQ organization.

    Args:
        package_name: The name of the package that was created.
        needs_description: A boolean indicating whether the package description was 
            provided or not.

    Returns:
        None

    Raises:
        None
    """
    log.warning(
        "[green]You have successfully created your package %s[/green]. To publish "
        "it, you need to:",
        package_name,
    )
    log.warning(
        "\tAssign an appropriate [bold green]version number[/bold green] in the "
        "pyproject.toml"
    )
    log.warning("\t[bold green]'git push`[/bold green] to remote in your private github")
    log.warning("\tCreate a pull request for your changes.")
    log.warning("\tSet up your pytest-cov key.")
    if needs_description:
        log.warning(
            "\tAdd a [bold green]package description[/bold green] in the pyproject.toml"
        )
    log.warning(
        "\tGet in touch with John Freeman and Andrew Mogan for review before they "
        "include it in the DUNEDAQ organization."
    )


def make_files(
    package_path: Path,
    requirements: list[str],
    applications: list[str],
    package_description: str,
    strict: bool,
) -> None:
    """Populate the skeleton repository with the default files."""
    log.debug("Creating [green]README.md[/green]")
    construct_default_readme_md(package_path, package_description)

    log.debug("Creating [green].gitignore[/green]")
    construct_default_gitignore(package_path)

    log.debug("Creating [green].github/workflows[/green]")
    construct_default_dot_github(package_path)

    log.debug("Creating [green].pre-commit-config.yaml[/green]")
    construct_default_pre_commit_config_yaml(package_path)

    log.debug("Creating [green]pyproject.toml[/green]")
    construct_default_pyproject_toml(
        package_path, package_description, requirements, applications, strict
    )

    log.debug("Creating __init__.py files")
    construct_inits(package_path)
    return


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("package-name", nargs=1, type=str)
@click.option(
    "-l",
    "--log-level",
    type=click.Choice(logging_log_level_keys, case_sensitive=False),
    default="INFO",
    help="Set the log level.",
)
@click.option(
    "-r",
    "--requirement",
    "requirements_tuple",
    type=str,
    multiple=True,
    help="Define requiements for the pyproject.toml as e.g. 'click'",
)
@click.option(
    "-rf",
    "--requirements-file",
    "requirements_file",
    type=str,
    multiple=False,
    help=(
        "Define requiements for the pyproject.toml by pointing to a requirements file "
        "(e.g. requirements.txt)."
    ),
)
@click.option(
    "-a",
    "--app-tuple",
    "applications_tuple",
    type=str,
    multiple=True,
    help="Create template scripts for applications to become available when installed",
)
@click.option(
    "-af",
    "--app-file",
    "applications_file",
    type=str,
    multiple=False,
    help=(
        "Define applications for the pyproject.toml by pointing to a file containing a "
        "list of application names (e.g. applications.txt)."
    ),
)
@click.option(
    "-p",
    "--package-description",
    "package_description",
    type=str,
    help="Package description for the pyproject.toml.",
)
@click.option(
    "-s", "--strict", is_flag=True, help="Strict mode. Recommended for production code."
)
def main(
    package_name: str,
    log_level: str,
    requirements_tuple: tuple[str],
    requirements_file: str,
    applications_tuple: tuple[str],
    applications_file: str,
    package_description: str,
    strict: bool,
) -> None:
    """Create a new DUNE-DAQ Python package.

    This script generates much of the standard Python code for a new DUNE DAQ package.

    Usage:
        create_python_dunedaq_package <package_name>

    The directory from which you run this script must be empty, except for a possible
    git/version control subdirectory. It is recommended that you run this script from
    <your_release_root>/pythoncode, as this is where the python-only packages are
    expected to be located in the DUNE DAQ software repository.

    For details on how to write a DUNE DAQ package, please refer to the official
    daq-cmake documentation which defines the DUNE-DAQ C++ repository standard at:
        https://dune-daq-sw.readthedocs.io/en/latest/packages/daq-cmake/

    For details on how to write a Python-only DUNE DAQ package, please refer to the
    official daqpyutils documentation at:
        https://dune-daq-sw.readthedocs.io/en/latest/packages/daqpyutils/
    """
    # Set up the logging instance
    log.setLevel(logging_log_level_to_int(log_level))

    # Perform the common checks on the package name and path
    if package_name == ".":
        log.error(
            "You passed '.' as the name of the package, which is not a valid package "
            "name. Perhaps you meant to use the tool [green]"
            "validate_python_dunedaq_package_structure[/]?"
        )
        sys.exit(1)
    package_path = Path.cwd() / package_name
    if package_path.exists() and package_path.is_dir():
        log.error(
            "[red]The directory %s already exists [/red]. Please remove it or choose "
            "a different package name.",
            package_name,
        )
        sys.exit(1)

    # Format the requirements and applications into lists
    requirements: list[str] = list(requirements_tuple)
    applications: list[str] = list(applications_tuple)

    # Unpack the requirements and applications from the files if provided
    applications = unpack_items(applications, applications_file)
    requirements = unpack_items(requirements, requirements_file)

    # Validate the package name and application names against the naming conventions
    validate_compliance_with_naming_conventions(package_name, applications)

    # Set up the package path
    package_path = Path.cwd() / Path(package_name)

    # Default string for package description if not provided
    needs_description: bool = not package_description or package_description.strip() == ""
    if package_description is None:
        package_description = "Description left as an exercise for the developer."


    make_subdirs(package_path, applications)
    log.debug("Subdirectories created in %s", package_path)
    make_files(package_path, requirements, applications, package_description, strict)
    summary_logging(package_name, needs_description)
    return


if __name__ == "__main__":
    main()
