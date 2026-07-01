import re
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import requests
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
    # Check local environment
    try:
        version(package_name)
        log.debug("Package '%s' found in local environment.", package_name)
        return True
    except PackageNotFoundError:
        log.debug("Package '%s' not found locally, checking PyPI...", package_name)

    # Check PyPI
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        response = requests.get(url, timeout=1)
        if response.status_code == 200:
            log.info("Package '%s' exists on PyPI.", package_name)
            return True
    except requests.exceptions.ConnectionError:
        log.error("Request to PyPI timed out while checking for package '%s' - is your web proxy off?", package_name)
        sys.exit(1)
    except requests.RequestException as e:
        log.exception(e)
        log.error("Requested package %s was not found in either the virtual environment or in PyPI, exiting.", package_name)
        sys.exit(1)

def item_is_formatted_with_version(item: str) -> bool:
    """
    Determine if the given item is formatted with a version number.

    Assumes that package names consist of alphanumeric characters, underscores, and
    hyphens, and either zero or two equals signs. If a single equals sign is used, this
    script determines that this item is a a project script specifier.

    >>> item_is_formatted_with_version("package_name==1.0.0")
    True
    >>> item_is_formatted_with_version("package_name")
    False
    >>> item_is_formatted_with_version("package_name=1.0.0")
    False

    Args:
        item: The item to check.

    Returns:
        bool: True if the item is formatted with a version number, False otherwise.

    Raises:
        None
    """
    return bool(re.match(r"^[a-zA-Z0-9_-]+==\d+\.\d+\.\d+$", item))

def item_is_formatted_in_kebab_case(item: str) -> bool:
    """
    Determine if the given item is defined in kebab-case.

    Assumes that application names consist of lowercase alphanumeric characters and
    hyphens, and do not contain underscores or equals signs.

    >>> item_is_formatted_in_kebab_case("application-name")
    True
    >>> item_is_formatted_in_kebab_case("application_name")
    False
    >>> item_is_formatted_in_kebab_case("ApplicationName")
    False

    Args:
        item: The item to check.

    Returns:
        bool: True if the item is defined in kebab-case, False otherwise.

    Raises:
        None
    """
    return bool(re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", item))

def item_is_package_name(item: str) -> bool:
    """
    Determine if the given item is a package name following the default conventions.

    Assumes that package names consist of alphanumeric characters, underscores, and
    hyphens, and either zero or two equals signs. If a single equals sign is used, this
    script determines that this item is a a project script specifier.

    >>> item_is_package_name("package-name==1.0.0")
    True
    >>> item_is_package_name("package-name")
    True
    >>> item_is_package_name("package-name=1.0.0")
    False
    >>> item_is_package_name("package_name")
    False

    Args:
        item: The item to check.

    Returns:
        bool: True if the item is a package name, False if it is a project script.

    Raises:
        None
    """

    package_name = item.split("==")[0] if "==" in item else item

    if item_is_formatted_with_version(item):
        return True
    elif "=" in item:
        return False
    elif not item_is_formatted_in_kebab_case(package_name):
        return True
    return False

def item_is_application_name(item: str) -> bool:
    """
    Determine if the given item is a package name or a project script.

    Assumes that package names consist of alphanumeric characters, underscores, and
    hyphens, and either zero or two equals signs. If a single equals sign is used, this
    script determines that this item is a a project script specifier.

    >>> item_is_package_name("package_name==1.0.0")
    True
    >>> item_is_package_name("package_name")
    True
    >>> item_is_package_name("package_name=1.0.0")
    False

    Args:
        item: The item to check.

    Returns:
        bool: True if the item is a package name, False if it is a project script.

    Raises:
        None
    """

    if item_is_formatted_in_kebab_case(item):
        return True
    return False

def validate_item_format_against_type(item: str, item_type: str) -> None:
    """
    Validate the given item based on its type.

    >>> validate_item_format_against_type("package_name==1.0.0", "requirements")
    None
    >>> validate_item_format_against_type("application-name", "applications")
    None
    >>> validate_item_format_against_type("package_name=1.0.0", "requirements")
    SystemExit: If the item is not valid for its type.

    Args:
        item: The item to validate.
        item_type: The type of the item, either "requirements" or "applications".

    Returns:
        None

    Raises:
        SystemExit: If the item is not valid for its type.
    """
    if item_type == "requirements":
        if not item_is_package_name(item):
            log.error(
                "Item %s is not a valid package name for requirements. It must be in "
                "the format 'package_name' or 'package_name==X.Y.Z'.",
                item,
            )
            sys.exit(1)
        return
    elif item_type == "applications":
        if not item_is_application_name(item):
            log.error(
                "Item %s is not a valid application name. It must be in kebab-case.",
                item,
            )
            sys.exit(1)
        return
    else:
        log.error("Invalid item_type provided: %s. Must be either 'requirements' or 'applications'.", item_type)
        sys.exit(1)

def strip_version_from_package_name(package_name: str) -> str:
    """
    Strip the version number from a package name if it is formatted with a version.

    >>> strip_version_from_package_name("package_name==1.0.0")
    'package_name'
    >>> strip_version_from_package_name("package_name")
    'package_name'

    Args:
        package_name: The package name to strip the version from.

    Returns:
        str: The package name without the version number.
    """
    if item_is_formatted_with_version(package_name):
        return package_name.split("==")[0]
    return package_name

def ingest_item_list(item_type: str, items: list[str]) -> list[str]:
    """
    Ingest a list of items and validate their format based on their type.

    >>> ingest_item_list("requirements", ["package_name==1.0.0", "package_name"])
    ['package_name', 'package_name']
    >>> ingest_item_list("applications", ["application-name", "another-application"])
    ['application-name', 'another-application']
    >>> ingest_item_list("requirements", ["package_name=1.0.0"])
    SystemExit: If any item is not valid for its type.
    >>> ingest_item_list("application_1", ["ApplicationName"])
    SystemExit: If any item is not valid for its type.

    Args:
        item_type: The type of items being ingested, either "requirements" or "applications".
        items: A list of items to ingest.

    Returns:
        list[str]: A list of validated items.

    Raises:
        SystemExit: If any item is not valid for its type.
    """
    ret_list: list[str] = []
    for item in items:
        validate_item_format_against_type(item, item_type)
        if item_type == "requirements":
            package_name = strip_version_from_package_name(item)
            validate_package(package_name)
            ret_list.extend(package_name)
        else:
            ret_list.append(item)

    return ret_list

def unpack_items(
    item_type: str | None = None,
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
        item_type: A string indicating the type of items being unpacked, either "requirements" or "applications".

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

    if not item_type or item_type not in ["requirements", "applications"]:
        log.error(
            "Invalid item_type provided: %s. Must be either 'requirements' or "
            "'applications'.",
            item_type,
        )
        sys.exit(1)

    # Unpack the items based on their type
    if isinstance(items, str):
        items = [items]
    if isinstance(items, list):
        ret.extend(ingest_item_list(item_type, items))

    # If a file is provided, parse its contents and add them to the list
    if items_file:
        log.info("Commencing parsing the contents of %s to list", items_file)

        # Validate that the file exists
        items_path = Path(items_file)
        if not items_path.is_file():
            log.error("%s is not a file or does not exist, exiting.", items_file)
            sys.exit(1)

        # Parse the file and format the relevant lines into a list of strings, inferring
        # their use based on their format, and ignoring both comments and empty lines
        file_entries: list[str] = []
        with items_path.open("r") as f:
            for line in f:
                line = line.strip()
                log.debug("Parsing %s", line)
                # Ignore empty lines and comments
                if not line or line.startswith("#"):
                    continue
                file_entries.append(line)
        
        ret.extend(ingest_item_list(item_type, file_entries))

    return ret


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
        [bold green]'git push`[/bold green] to remote in your private github, and set up a new remote if you haven't already
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
    log.warning("\t[bold green]'git push`[/bold green] to remote in your private github, and set up a new remote if you haven't already")
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
    log.info("Using requirements: %s", requirements)
    applications: list[str] = list(applications_tuple)

    # Unpack the requirements and applications from the files if provided
    applications = unpack_items("applications", applications, applications_file)
    requirements = unpack_items("requirements", requirements, requirements_file)

    # Validate the package name and application names against the naming conventions
    validate_compliance_with_naming_conventions(package_name, applications)

    # Set up the package path
    package_path = Path.cwd() / Path(package_name)
    log.info("Creating package %s in %s", package_name, package_path)

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
