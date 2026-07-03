from daqpyutils.repository_handling.utils import (
    validate_package,
    item_is_formatted_with_version,
    item_is_formatted_in_kebab_case,
    item_is_package_name,
    item_is_application_name,
    validate_item_format_against_type,
    ingest_item_list,
    unpack_items,
    strip_version_from_package_name,
    validate_compliance_with_naming_conventions,
    setup_dot_git,
    make_subdirs,
    populate_template,
    copy_template,
    construct_default_readme_md,
    construct_default_gitignore,
    construct_default_dot_github,
    construct_default_pre_commit_config_yaml,
    construct_application_file,
    parse_applications,
    construct_default_pyproject_toml,
    construct_inits,
    make_files,
)
import pytest
import tempfile
from pathlib import Path

def test_validate_package() -> None:
    """
    Test the validate_package function with valid and invalid package names.
    """
    assert validate_package("daqpyutils") is True
    assert validate_package("numpy") is True
    # Invalid package names, also covered for testing without internet access
    with pytest.raises(SystemExit):
        validate_package("daqpyutils-1..0")
    with pytest.raises(SystemExit):
        validate_package("daqpyutils-1.0.0-beta+build..123..456")

def test_item_is_formatted_with_version() -> None:
    """
    Test the item_is_formatted_with_version function with valid and invalid formats.
    """
    assert item_is_formatted_with_version("daqpyutils==1.0.0") is True
    # Invalid formats
    assert item_is_formatted_with_version("daqpyutils-1.0.0") is False
    assert item_is_formatted_with_version("daqpyutils=1.0.0-beta+build..123") is False
    assert item_is_formatted_with_version("daqpyutils=1.0.0-beta+build.123+build..456") is False

def test_item_is_formatted_in_kebab_case() -> None:
    """
    Test the item_is_formatted_in_kebab_case function with valid and invalid formats.
    """
    assert item_is_formatted_in_kebab_case("daqpyutils") is True
    assert item_is_formatted_in_kebab_case("daq-py-utils") is True
    # Invalid formats
    assert item_is_formatted_in_kebab_case("daq_py_utils") is False
    assert item_is_formatted_in_kebab_case("daqPyUtils") is False
    assert item_is_formatted_in_kebab_case("daq-py-utils-1.0.0") is False
    assert item_is_formatted_in_kebab_case("daq-py-utils-1.0.0-beta") is False

def test_item_is_package_name() -> None:
    """
    Test the item_is_package_name function with valid and invalid package names.
    """
    assert item_is_package_name("daqpyutils") is True
    assert item_is_package_name("numpy") is True
    assert item_is_package_name("kafka") is True
    assert item_is_package_name("daqpyutils-1.-beta") is True
    assert item_is_package_name("daqpyutils-1..beta") is True
    assert item_is_package_name("daqPyUtils") is True
    assert item_is_package_name("daq_py_utils") is True
    # Invalid package names
    assert item_is_package_name("daqpyutils=1..0") is False



def test_validate_item_format_against_type() -> None:
    """
    Test the validate_item_format_against_type function with various item types and formats.
    """
    # Valid formats for the given types
    validate_item_format_against_type("daqpyutils==1.0.0", "requirements")
    validate_item_format_against_type("create-python-dunedaq-package", "applications")


@pytest.mark.parametrize("item, item_type", [
    ("click=1.0.0", "requirements"),
    ("this_is_camel_case", "applications"),
])
def test_validate_item_format_against_type_failures(item: str, item_type: str) -> None:
    """
    Test the validate_item_format_against_type function with invalid formats.
    """
    with pytest.raises(SystemExit) as excinfo:
        validate_item_format_against_type(item, item_type)
    assert excinfo.value.code == 1


def test_strip_version_from_package_name() -> None:
    """
    Test the strip_version_from_package_name function with valid and invalid package names.
    """
    assert strip_version_from_package_name("daqpyutils==1.0.0") == "daqpyutils"
    # Invalid formats
    strip_version_from_package_name("daqpyutils-1.0.0") == "daqpyutils-1.0.0"
    strip_version_from_package_name("daqpyutils=1.0.0-beta+build..123") == "daqpyutils=1.0.0-beta+build..123"

def test_ingest_item_list() -> None:
    """
    Test the ingest_item_list function with a list of items.
    """

    # Test parsing requirements
    test_requirement = ["daqpyutils==1.0.0", "numpy==1.21.0", "scipy"]
    ingested_requirements = ingest_item_list("requirements", test_requirement)
    assert len(ingested_requirements) == 3
    assert ingested_requirements[0] == "daqpyutils"
    assert ingested_requirements[1] == "numpy"
    assert ingested_requirements[2] == "scipy"

    # Test parsing applications
    test_applications = ["create-python-dunedaq-package", "another-application"]
    ingested_applications = ingest_item_list("applications", test_applications)
    assert len(ingested_applications) == 2
    assert ingested_applications[0] == "create-python-dunedaq-package"
    assert ingested_applications[1] == "another-application"

    # Test parsing non-existent applications
    with pytest.raises(SystemExit):
        ingest_item_list("application", ["non-existent-application"])

def test_unpack_items() -> None:
    """
    Test the unpack_items function with a list of items.
    """

    # Test ingesting a list of requirements
    test_requirements = ["daqpyutils==1.0.0", "numpy==1.21.0", "scipy"]
    unpacked_items = unpack_items("requirements", items=test_requirements)
    assert len(unpacked_items) == 3
    assert unpacked_items[0] == "daqpyutils"
    assert unpacked_items[1] == "numpy"
    assert unpacked_items[2] == "scipy"

    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        # Test ingesting a requirements file only with empty lines and comments
        temp_file.write(b"daqpyutils==1.0.0\nnumpy==1.21.0\n#scipy\n")
        temp_file.seek(0)
        temp_file_path = temp_file.name
        unpacked_items_from_file = unpack_items("requirements", items_file=temp_file_path)
        assert len(unpacked_items_from_file) == 2
        assert unpacked_items_from_file[0] == "daqpyutils"
        assert unpacked_items_from_file[1] == "numpy"
        assert "scipy" not in unpacked_items_from_file

        # Test ingesting a requirements file and from a tuple simultaneously
        requirements_list = ["matplotlib==3.11.0"]
        all_unpacked_items = unpack_items("requirements", items=requirements_list, items_file=temp_file_path)
        assert len(all_unpacked_items) == 3
        assert all_unpacked_items[0] == "matplotlib"
        assert all_unpacked_items[1] == "daqpyutils"
        assert all_unpacked_items[2] == "numpy"
        assert "scipy" not in all_unpacked_items

    # Test ingesting a non-existent requirements file
    with pytest.raises(SystemExit):
        unpack_items("requirements", items_file="non_existent_file.txt")

    # Test ingesting a requirements file with invalid formats
    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        temp_file.write(b"daqpyutils==1.0.0\ninvalid-format\n")
        temp_file.seek(0)
        temp_file_path = temp_file.name
        with pytest.raises(SystemExit):
            unpack_items("requirements", items_file=temp_file_path)

    # Test ingesting a requirements file with invalid formats and a valid tuple simultaneously
    with tempfile.NamedTemporaryFile(delete=True) as temp_file:
        temp_file.write(b"daqpyutils==1.0.0\ninvalid_format\n")
        temp_file.seek(0)
        temp_file_path = temp_file.name
        requirements_list = ["matplotlib==3.11.0"]
        with pytest.raises(SystemExit):
            unpack_items("requirements", items=requirements_list, items_file=temp_file_path)

    # Test ingesting a list of applications
    test_applications = ["create-python-dunedaq-package", "another-application"]
    unpacked_applications = unpack_items("applications", items=test_applications)
    assert len(unpacked_applications) == 2
    assert unpacked_applications[0] == "create-python-dunedaq-package"
    assert unpacked_applications[1] == "another-application"

    # Test ingesting an incorrectly formatted application
    with pytest.raises(SystemExit):
        unpack_items("applications", items=["application_names_should_be_in_kebab_case"])

def test_validate_compliance_with_naming_conventions() -> None:
    """
    Test the validate_compliance_with_naming_conventions function with valid and invalid package names.
    """
    # Valid package names
    validate_compliance_with_naming_conventions("daqpyutils", []) 
    validate_compliance_with_naming_conventions("numpy", [])
    validate_compliance_with_naming_conventions("kafka", [])

    # Validate application names
    validate_compliance_with_naming_conventions("daqpyutils", ["create-python-dunedaq-application", "some-test-application"])

    # Validate combination
    validate_compliance_with_naming_conventions("daqpyutils", ["create-python-dunedaq-application", "some-test-application"])

    # Invalid package names
    with pytest.raises(SystemExit):
        validate_compliance_with_naming_conventions("daqpyutils_1..0", [])
    with pytest.raises(SystemExit):
        validate_compliance_with_naming_conventions("daqpyutils_1.0.0-beta+build..123..456", [])

    # Invalid application names
    with pytest.raises(SystemExit):
        validate_compliance_with_naming_conventions("daqpyutils", ["create_python_dunedaq_application"])

    # Invalid combination
    with pytest.raises(SystemExit):
        validate_compliance_with_naming_conventions("daqpyutils_1..0", ["create_python_dunedaq_application"])

def test_setup_dot_git(tmp_path: Path) -> None:
    """
    Test the setup_dot_git function by creating a temporary directory and checking if the .git directory is created.
    """
    # Create a temporary directory
    temp_dir = tmp_path / "test_repo"
    temp_dir.mkdir()

    # Call the setup_dot_git function
    setup_dot_git(temp_dir)

    # Check if the .git directory is created
    git_dir = temp_dir / ".git"
    assert git_dir.exists() and git_dir.is_dir()

def test_make_subdirs(tmp_path: Path) -> None:
    """
    Test the make_subdirs function by creating a temporary directory and checking if the specified subdirectories are created.
    """
    # Create a temporary directory
    temp_dir = tmp_path / "test_repo"
    temp_dir.mkdir()

    # Define subdirectories to create
    subdirs = ["src", "tests", "docs"]

    # Call the make_subdirs function
    make_subdirs(temp_dir, subdirs)

    # Check if the specified subdirectories are created
    for subdir in subdirs:
        subdir_path = temp_dir / subdir
        assert subdir_path.exists() and subdir_path.is_dir()

def test_populate_template(tmp_path: Path) -> None:
    """
    Test the populate_template function by creating a temporary directory and checking if the template files are populated correctly.
    """
    # Create a temporary directory
    temp_dir = tmp_path / "test_repo"
    temp_dir.mkdir()

    # Define template content
    template_content = "This is a test template."

    # Create a temporary template file
    template_file = temp_dir / "template.jinja"
    template_file.write_text(template_content)

    # Create a target output dir
    output_path = temp_dir / "output.txt"

    # Call the populate_template function
    populate_template(template_file, {"test_var": "THIS_SHOULD_NOT_BE_PRESENT"}, output_path)

    # Check if the template file is populated correctly
    assert output_path.exists() and output_path.read_text() == template_content
    assert "THIS_SHOULD_NOT_BE_PRESENT" not in output_path.read_text()

def test_copy_template(tmp_path: Path) -> None:
    """
    Test the copy_template function by creating a temporary directory and checking if the template files are copied correctly.
    """
    # Create a temporary directory
    temp_dir = tmp_path / "test_repo"
    temp_dir.mkdir()

    # Define template content
    gitignore_template_content = "xml"

    # Create a temporary template file
    output_path = temp_dir / "output.txt"

    # Call the copy_template function
    copy_template("gitignore.jinja", output_path)

    # Check if the template file is copied correctly
    assert output_path.exists() and gitignore_template_content in output_path.read_text()

def test_construct_default_readme_md(tmp_path: Path) -> None:
    """
    Test the construct_default_readme_md function by creating a temporary directory and checking if the README.md file is created correctly.
    """
    # Create a temporary directory
    package_name = "test_repo"
    temp_dir = tmp_path / package_name
    temp_dir.mkdir()

    # Set up the package description
    package_description = "This is a test package."

    # Call the construct_default_readme_md function
    construct_default_readme_md(temp_dir, package_description)

    # Check if the README.md file is created correctly
    readme_file = temp_dir / "docs" / "README.md"
    assert readme_file.exists() 
    assert readme_file.read_text().startswith("# ")
    assert package_name in readme_file.read_text()
    assert package_description in readme_file.read_text()

def test_construct_default_gitignore(tmp_path: Path) -> None:
    """
    Test the construct_default_gitignore function by creating a temporary directory and checking if the .gitignore file is created correctly.
    """
    # Create a temporary directory
    temp_dir = tmp_path / "test_repo"
    temp_dir.mkdir()

    # Call the construct_default_gitignore function
    construct_default_gitignore(temp_dir)

    # Check if the .gitignore file is created correctly
    gitignore_file = temp_dir / ".gitignore"
    assert gitignore_file.exists() 
    assert gitignore_file.read_text().startswith("#")
    assert "xml" in gitignore_file.read_text()

def test_construct_default_dot_github(tmp_path: Path) -> None:
    """
    Test the construct_default_dot_github function by creating a temporary directory and checking if the .github directory is created correctly.
    """
    # Create a temporary directory
    temp_dir = tmp_path / "test_repo"
    temp_dir.mkdir()

    # Call the construct_default_dot_github function
    construct_default_dot_github(temp_dir)

    # Check if the .github directory is created correctly
    github_dir = temp_dir / ".github"
    assert github_dir.exists() and github_dir.is_dir()

    # Check if the pull request template exists
    pr_template_file = github_dir / "pull_request_template.md"
    assert pr_template_file.exists() and pr_template_file.is_file()

    # Check if the default workflows are created correctly
    workflows_dir = github_dir / "workflows"
    assert workflows_dir.exists() and workflows_dir.is_dir()

def test_construct_default_pre_commit_config_yaml(tmp_path: Path) -> None:
    """
    Test the construct_default_pre_commit_config_yaml function by creating a temporary directory and checking if the .pre-commit-config.yaml file is created correctly.
    """
    # Create a temporary directory
    temp_dir = tmp_path / "test_repo"
    temp_dir.mkdir()

    # Call the construct_default_pre_commit_config_yaml function
    construct_default_pre_commit_config_yaml(temp_dir)

    # Check if the .pre-commit-config.yaml file is created correctly
    pre_commit_file = temp_dir / ".pre-commit-config.yaml"
    assert pre_commit_file.exists() and pre_commit_file.is_file()
    assert "ruff" in pre_commit_file.read_text()

def test_construct_application_file(tmp_path: Path) -> None:
    """
    Test the construct_application_file function by creating a temporary directory and checking if the application file is created correctly.
    """
    # Create a temporary directory
    repo_name = "test_repo"
    temp_dir = tmp_path / repo_name
    temp_dir.mkdir()

    # Define application name
    application_name = "test-application"

    # Call the construct_application_file function
    construct_application_file(application_name, temp_dir / "src" / repo_name / "apps" / f"{application_name}.py")

    # Check if the application file is created correctly
    application_file = temp_dir / "src" / repo_name / "apps" / f"{application_name}.py"
    assert application_file.exists() and application_file.is_file()
    assert "main" in application_file.read_text()
    assert 'if __name__ == \"__main__\":' in application_file.read_text()

def test_parse_applications(tmp_path: Path) -> None:
    """
    Test the parse_applications function with valid and invalid application names.
    """

    # Create a temporary directory 
    repo_name = "test_repo"
    temp_dir = tmp_path / repo_name
    temp_dir.mkdir()

    # Construct some applications
    app1 = "test-application"
    app2 = "another-test-application"
    application_names = [app1, app2]
    application_entry_points = parse_applications(temp_dir, application_names)

    # Assert that the files have been created
    for app_name in application_names:
        app_file = temp_dir / "src" / repo_name / "apps" / f"{app_name}.py"
        assert app_file.exists() and app_file.is_file()
        assert "main" in app_file.read_text()
        assert 'if __name__ == \"__main__\":' in app_file.read_text()

    # Check the entry point definition
    for app_name in application_names:
        assert app_name in application_entry_points
        assert f'{app_name} = \"{repo_name}.apps.{app_name}:main\"' in application_entry_points

    # Check no newline at end of string
    assert not application_entry_points.endswith("\n")

def test_construct_default_pyproject_toml(tmp_path: Path) -> None:
    """
    Test the construct_default_pyproject_toml function by creating a temporary directory and checking if the pyproject.toml file is created correctly.
    """
    # Create a temporary directory
    repo_name = "test_repo"
    temp_dir = tmp_path / repo_name
    temp_dir.mkdir()

    # Create other required metadata
    package_description = "This is a test package."
    requirements = ["daqpyutils", "click==8.1.3"]
    applications = ["test-app-1", "test-app-2"]
    strict = True

    # Call the construct_default_pyproject_toml function
    construct_default_pyproject_toml(temp_dir, package_description, requirements, applications, strict)

    # Check if the pyproject.toml file is created correctly
    pyproject_file = temp_dir / "pyproject.toml"
    assert pyproject_file.exists() and pyproject_file.is_file()
    assert "setuptools" in pyproject_file.read_text()
    assert not "{{" in pyproject_file.read_text() and not "}}" in pyproject_file.read_text() # Ensure no template placeholders remain
    assert "mypy" in pyproject_file.read_text()


    # Check if the requirements are included in the pyproject.toml
    for requirement in requirements:
        assert requirement in pyproject_file.read_text()

    # Check if the applications are included in the pyproject.toml
    for application in applications:
        assert f'{application} = \"{repo_name}.apps.{application}:main\"' in pyproject_file.read_text()

def test_make_files(tmp_path: Path) -> None:
    """
    Test the make_files function by creating a temporary directory and checking if the files are created correctly.
    """
    # Create a temporary directory
    repo_name = "test_repo"
    temp_dir = tmp_path / repo_name
    temp_dir.mkdir()

    # Create package metadata
    requirements = ["daqpyutils", "click==8.1.3"]
    applications = ["test-app-1", "test-app-2"]
    package_description = "This is a test package."
    strict=False

    # Call the make_files function
    make_files(temp_dir, requirements, applications, package_description, strict)

    # Check if the repo has a pyproject.toml
    pyproject_file = temp_dir / "pyproject.toml"
    assert pyproject_file.exists() and pyproject_file.is_file()

    # Check if the repo has a README.md
    readme_file = temp_dir / "docs" / "README.md"
    assert readme_file.exists() and readme_file.is_file()

    # Check if the repo has a .gitignore
    gitignore_file = temp_dir / ".gitignore"
    assert gitignore_file.exists() and gitignore_file.is_file()

    # Check if the repo has a .github directory
    github_dir = temp_dir / ".github"
    assert github_dir.exists() and github_dir.is_dir()

    # Check if the repo has a .github/workflows directory
    workflows_dir = github_dir / "workflows"
    assert workflows_dir.exists() and workflows_dir.is_dir()

    # Check if the repo has a .github/pull_request_template.md
    pr_template_file = github_dir / "pull_request_template.md"
    assert pr_template_file.exists() and pr_template_file.is_file()

    # Check if the repo has a .github/workflows/pytest.yml
    pytest_workflow_file = workflows_dir / "pytest.yml"
    assert pytest_workflow_file.exists() and pytest_workflow_file.is_file()

    # Check if the repo has a .pre-commit-config.yaml
    pre_commit_file = temp_dir / ".pre-commit-config.yaml"
    assert pre_commit_file.exists() and pre_commit_file.is_file()

    # Check if the repo has a src directory with the package name
    src_dir = temp_dir / "src" / repo_name
    assert src_dir.exists() and src_dir.is_dir()

    # Check if the repo has an apps directory with the applications
    apps_dir = src_dir / "apps"
    assert apps_dir.exists() and apps_dir.is_dir()

    # Check if the repo has __init__.py files in the src directory
    init_file_src = src_dir / "__init__.py"
    assert init_file_src.exists() and init_file_src.is_file()

    # Check if the repo has __init__.py files in the integtest directory
    integtest_dir = src_dir / "integtest"
    assert integtest_dir.exists() and integtest_dir.is_dir()
    init_file_integtest = integtest_dir / "__init__.py"
    assert not init_file_integtest.exists()

# tests/repository_handling/test_utils.py::test_parse_applications FAILED
# tests/repository_handling/test_utils.py::test_construct_default_pyproject_toml FAILED
# tests/repository_handling/test_utils.py::test_construct_inits FAILED
# tests/repository_handling/test_utils.py::test_make_files FAILED