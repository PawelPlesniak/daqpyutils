import sys
from pathlib import Path

import click
from daqpytools.logging.levels import logging_log_level_keys, logging_log_level_to_int
from daqpytools.logging.logger import get_daq_logger

from daqpyutils.repository_handling.utils import (
    make_files,
    make_subdirs,
    unpack_items,
    validate_compliance_with_naming_conventions,
)

template_path = Path(__file__).parent.parent / "templates"
log = get_daq_logger(
    logger_name="daqpyutils.create_python_dunedaq_package", rich_handler=True
)
template_variables: dict[str, str | bool] = {}


def summary_logging(package_name: str, needs_description: bool) -> None:
    """
    Log future actions to comission the created package into the DUNE-DAQ organization.

    Summarize the package creation, and the remaining tasks required to integrate the
    package with the DUNE-DAQ github oragnization.

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
    log.warning(
        "\t[bold green]'git push`[/bold green] to remote in your private github, and "
        "set up a new remote if you haven't already"
    )
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
    multiple=False,  # If multiple are used in CLI, only the last instance is used.
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
    multiple=False,  # If multiple are used in CLI, only the last instance is used.
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
    applications = unpack_items("applications", applications, applications_file)
    log.info("Applications to be created: %s", applications)
    requirements = unpack_items("requirements", requirements, requirements_file)
    log.info("Requirements to be added to pyproject.toml: %s", requirements)

    # Validate the package name and application names against the naming conventions
    validate_compliance_with_naming_conventions(package_name, applications)

    # Set up the package path
    package_path = Path.cwd() / Path(package_name)
    log.info("Creating package %s in %s", package_name, package_path)

    # Default string for package description if not provided
    needs_description: bool = (
        not package_description or package_description.strip() == ""
    )
    if package_description is None:
        package_description = "Description left as an exercise for the developer."

    make_subdirs(package_path, applications)
    log.debug("Subdirectories created in %s", package_path)
    make_files(package_path, requirements, applications, package_description, strict)
    summary_logging(package_name, needs_description)
    return


if __name__ == "__main__":
    main()
