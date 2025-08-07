import os
import re
import tempfile
from pathlib import Path

import pytest
from _pytest.logging import LogCaptureFixture
from click.testing import CliRunner, Result

from daqpyutils.apps.__main_create_python_dunedaq_package__ import (
    construct_application_file,
    construct_default_dot_github,
    construct_default_gitignore,
    construct_default_pre_commit_config_yaml,
    construct_default_pyproject_toml,
    construct_default_readme_md,
    copy_template,
    format_requirements,
    make_subdirs,
    parse_applications,
    unpack_items,
    validate_names,
)
from daqpyutils.apps.__main_create_python_dunedaq_package__ import (
    main as create_python_dunedaq_package,
)

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
runner = CliRunner()
test_package_name = "testPackage"


def strip_ansi(text: str) -> str:
    text = ANSI_ESCAPE_RE.sub("", text)
    return text.replace("\n", "").replace("\r", "")


def test_incorrect_log_level() -> None:
    """Test that the app throws when an incorrect log level is passed."""
    result: Result = runner.invoke(
        create_python_dunedaq_package, [test_package_name, "-l", "INVALID"]
    )
    output: str = strip_ansi(result.output)
    assert result.exit_code != 0
    err_str: str = (
        "Invalid value for '-l' / '--log-level': 'INVALID' is not one of 'CRITICAL', "
        "'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'"
    )
    assert err_str in output


def test_create_this_package() -> None:
    """Test that the app throws when creating package '.'."""
    result = runner.invoke(create_python_dunedaq_package, ["."])
    output = strip_ansi(result.output)
    assert result.exit_code != 0
    assert "You passed '.' as the name of the package." in output
    assert (
        "Perhaps you meant to use the tool validate_python_dunedaq_package_structure?"
        in output
    )


def test_unpack_items() -> None:
    """Test that unpack_items correctly unpacks a list of items."""
    assert unpack_items() == []
    assert unpack_items(None) == []
    assert unpack_items([]) == []
    assert unpack_items("item1") == ["item1"]
    items = ["item1", "item2", "item3"]
    unpacked = unpack_items(items)
    assert unpacked == items
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmpfile:
        tmpfile.write("itemA\nitemB\nitemC\n")
        tmpfile.flush()
        tmpfile.seek(0)
        items_from_file = [line.strip() for line in tmpfile if line.strip()]
        unpacked_from_file = unpack_items(items_from_file)
        assert unpacked_from_file == ["itemA", "itemB", "itemC"]
    os.unlink(tmpfile.name)


def test_unpack_items_fail(caplog: LogCaptureFixture) -> None:
    """Test that unpack_items raises an error for invalid input."""
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmpfile:
        data_as_tuple = ("item1", "item2", "item3")
        with caplog.at_level("ERROR"):
            with pytest.raises(SystemExit) as exc_info:
                unpack_items(data_as_tuple)
        assert exc_info.value.code == 1
        assert (
            "Invalid input type. Expected a list of strings or a single string, got"
            f" {type(data_as_tuple)}." in caplog.text
        )
    os.unlink(tmpfile.name)


def test_validate_names() -> None:
    """Test that validate_names correctly validates package names."""
    validate_names(test_package_name, ["app1", "app2"])
    with pytest.raises(SystemExit):
        validate_names(".", ["app1", "app2"])
    with pytest.raises(SystemExit):
        validate_names("test_package", ["app1", "app2"])
    with pytest.raises(SystemExit):
        validate_names(test_package_name, ["app1", "app2", "invalid-app-name!"])
    with pytest.raises(SystemExit):
        validate_names(test_package_name, ["app1", "app2", "123invalid_start"])


def test_make_subdirs() -> None:
    """Test that make_subdirs creates the expected directories."""
    with tempfile.TemporaryDirectory() as tempdir:
        subdirs = ["src", "tests", "docs"]
        make_subdirs(Path(tempdir), subdirs)
        for subdir in subdirs:
            assert os.path.isdir(os.path.join(tempdir, subdir))


def test_copy_template() -> None:
    """Test that copy_template copies the template files to the target directory."""
    with tempfile.TemporaryDirectory() as tempdir:
        copy_template("gitignore.jinja", Path(tempdir) / ".gitignore")
        assert (Path(tempdir) / ".gitignore").exists()


def test_construct_default_readme_md() -> None:
    """Test that construct_default_readme_md creates and writes a valid README.md."""
    with tempfile.TemporaryDirectory() as tempdir:
        os.makedirs(Path(tempdir) / test_package_name / "docs", exist_ok=True)
        description = "This is a test for the README.md construction."
        construct_default_readme_md(Path(tempdir) / test_package_name, description)
        readme_path = Path(tempdir) / test_package_name / "docs" / "README.md"
        assert readme_path.exists()
        with open(readme_path) as readme_file:
            content = readme_file.read()
            assert test_package_name in content
            assert description in content


def test_construct_default_gitignore() -> None:
    """Test that construct_default_gitignore creates a valid .gitignore file."""
    with tempfile.TemporaryDirectory() as tempdir:
        package_path = Path(tempdir) / test_package_name
        os.makedirs(package_path, exist_ok=True)
        construct_default_gitignore(package_path)
        gitignore_path = package_path / ".gitignore"
        assert gitignore_path.exists()
        with open(gitignore_path) as gitignore_file:
            content = gitignore_file.read()
            assert "log*" in content
            assert "__pycache__" in content


def test_construct_default_dot_github() -> None:
    """Test that construct_default_dot_github creates the expected workflows."""
    with tempfile.TemporaryDirectory() as tempdir:
        package_path = Path(tempdir) / test_package_name
        os.makedirs(package_path, exist_ok=True)
        construct_default_dot_github(package_path)
        workflows_path = package_path / ".github"
        assert workflows_path.exists()
        for workflow_file in ["pull_request_template.md", "dependabot.yml"]:
            assert (workflows_path / workflow_file).exists()
        workflows_path = workflows_path / "workflows"
        assert workflows_path.exists()
        for workflow_file in [
            "check_links.yml",
            "lint.yml",
            "test.yml",
            "track_new_issues.yml",
            "track_new_prs.yml",
        ]:
            assert (workflows_path / workflow_file).exists()


def test_construct_default_pre_commit_config_yaml() -> None:
    """Test that construct_default_pre_commit_config_yaml creates a valid file."""
    with tempfile.TemporaryDirectory() as tempdir:
        package_path = Path(tempdir) / test_package_name
        os.makedirs(package_path, exist_ok=True)
        construct_default_pre_commit_config_yaml(package_path)
        pre_commit_path = package_path / ".pre-commit-config.yaml"
        assert pre_commit_path.exists(), f"{pre_commit_path} does not exist"
        assert pre_commit_path.is_file(), f"{pre_commit_path} is not a file"
        with open(pre_commit_path) as pre_commit_file:
            content = pre_commit_file.read()
            assert "repos:" in content
            assert "- repo:" in content
            assert "ruff" in content
            assert "black" in content
            assert "pytest" in content


def test_construct_application_file() -> None:
    """Test that construct_application_file creates a valid application file."""
    with tempfile.TemporaryDirectory() as tempdir:
        app_name = "test_app"
        app_path = (
            Path(tempdir) / test_package_name / "apps" / f"__main_{app_name}__.py"
        )
        os.makedirs(app_path.parent, exist_ok=True)
        construct_application_file(app_name, app_path)
        assert app_path.exists()
        with open(app_path) as app_file:
            content = app_file.read()
            assert "def main() -> None:" in content
            assert 'if __name__ == "__main__":' in content


def test_parse_applications() -> None:
    """Test that parse_applications constructs entry points correctly."""
    with tempfile.TemporaryDirectory() as tempdir:
        package_path = Path(tempdir) / test_package_name
        app_path = package_path / "src" / test_package_name / "apps"
        os.makedirs(app_path, exist_ok=True)
        applications = ["app1", "app2"]
        parse_applications(package_path, applications)
        app_file_names = [f"__main_{app}__.py" for app in applications]
        expected_app_files = [
            app_path / app_file_name for app_file_name in app_file_names
        ]
        generated_app_files = [file for file in app_path.glob("*.py") if file.is_file()]
        assert set(expected_app_files) == set(generated_app_files)


def test_format_requirements() -> None:
    """Test that format_requirements formats requirements correctly."""
    click_version = "8.1.7"
    requirements_with_version = [f"click=={click_version}"]
    formatted_requirements = format_requirements(requirements_with_version)
    assert formatted_requirements == requirements_with_version

    requirements_without_version = ["click"]
    assert (
        format_requirements(requirements_without_version) == requirements_with_version
    )

    with pytest.raises(SystemExit):
        format_requirements(["non_existent_package"])

    with pytest.raises(SystemExit):
        format_requirements(["non_existent_package==0.1.0"])

    # Test with an empty list
    assert format_requirements([]) == []


def test_construct_default_pyproject_toml() -> None:
    """Test that construct_default_pyproject_toml creates a valid pyproject.toml."""
    test_description = "Test Package"
    requirements = ["click==8.1.7"]
    applications = ["app1", "app2"]
    strict_requirements = True
    with tempfile.TemporaryDirectory() as tempdir:
        package_path = Path(tempdir) / test_package_name
        os.makedirs(package_path, exist_ok=True)
        construct_default_pyproject_toml(
            package_path,
            test_description,
            requirements,
            applications,
            strict_requirements,
        )
        pyproject_path = package_path / "pyproject.toml"
        assert pyproject_path.exists()
        with open(pyproject_path) as pyproject_file:
            content = pyproject_file.read()
            assert "setuptools" in content
            assert "[project]" in content
            assert f'name = "{test_package_name}"' in content
            assert 'description = "Test Package"' in content
    # TODO - Add tests for other generated files
