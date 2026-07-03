import os
import re
import tempfile
from pathlib import Path

import pytest
from _pytest.logging import LogCaptureFixture
from click.testing import CliRunner, Result
from daqpyutils.apps.create_python_dunedaq_package import summary_logging
from daqpyutils.apps.create_python_dunedaq_package import (
    main as create_python_dunedaq_package,
)
import subprocess
import sys

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
runner = CliRunner()
test_package_name = "test_daqpyutils_package"


def strip_ansi(text: str) -> str:
    """
    Strip ANSI escape sequences from the given text and remove newlines and carriage 
    returns.

    >>> strip_ansi("\\x1b[31mHello\\x1b[0m\\nWorld")
    'HelloWorld'

    Args:
        text (str): The input text from which to remove ANSI escape sequences.

    Returns:
        str: The text with ANSI escape sequences removed and newlines/carriage returns
        replaced with empty strings.

    Raises:
        None
    """
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
        "Invalid value for '-l' / '--log-level': 'INVALID' is not one of 'critical', "
        "'error', 'warning', 'info', 'debug', 'notset'."
    )
    assert err_str in output


def test_create_this_package() -> None:
    """Test that the app throws when creating package '.'."""
    result = runner.invoke(create_python_dunedaq_package, ["."])
    output = strip_ansi(result.output)
    assert result.exit_code != 0
    assert "You passed '.' as the name of the package" in output
    assert (
        "Perhaps you meant to use the tool validate_python_dunedaq_package_structure?"
        in output
    )

def test_create_a_package_and_validate(tmp_path: Path) -> None:
    """
    Test that a test repository can be generated, is pip installable, has runnable
    applications, and that it passes all the checks
    """
    runner = CliRunner()
    
    # 1. Setup temporary paths using pytest's tmp_path
    requirements_file = tmp_path / "requirements.txt"
    requirements_file.write_text("grpcio\n")
    
    application_file = tmp_path / "apps.txt"
    application_file.write_text("test_daqpyutils_app_creation_1\n")
    
    # 2. Invoke the CLI command
    # Note: Using str(path) is safer for click arguments
    result = runner.invoke(
        create_python_dunedaq_package, 
        [
            "-l", "info"
            "test-package-name", 
            "-r", "click", 
            "-rf", str(requirements_file),
            "-a", "test_daqpyutils_app_creation_2",
            "-af", str(application_file),
            "-p", "Test of the package creation",
            "-s"
        ], 
        obj={"root_path": tmp_path}
    )
    
    # 3. Assert CLI success
    assert result.exit_code == 0
    
    # 4. Verify directory structure
    package_dir = tmp_path / "test-package-name"
    assert package_dir.exists(), "Package directory was not created"
    pyproject_toml_file_path = package_dir / "pyproject.toml"
    assert pyproject_toml_file_path.exists(), "pyproject.toml was not created"
    gitignore_file_path = package_dir / ".gitignore"
    assert gitignore_file_path.exists(), ".gitignore was not created"
    github_dir = package_dir / ".github"
    assert github_dir.exists(), ".github directory was not created"
    github_workflow_dir = github_dir / "workflows"
    assert github_workflow_dir.exists(), ".github/workflows directory was not created"
    pull_request_template_file_path = github_dir / "PULL_REQUEST_TEMPLATE.md"
    assert pull_request_template_file_path.exists(), "PULL_REQUEST_TEMPLATE.md was not created"
    lint_workflow_file_path = github_workflow_dir / "lint.yml"
    assert lint_workflow_file_path.exists(), "lint.yml was not created"
    pytest_workflow_file_path = github_workflow_dir / "pytest.yml"
    assert pytest_workflow_file_path.exists(), "pytest.yml was not created"
    track_new_issues_workflow_file_path = github_workflow_dir / "track_new_issues.yml"
    assert track_new_issues_workflow_file_path.exists(), "track_new_issues.yml was not created"
    track_new_prs_workflow_file_path = github_workflow_dir / "track_new_prs.yml"
    assert track_new_prs_workflow_file_path.exists(), "track_new_prs.yml was not created"
    readme_file_path = package_dir / "README.md"
    assert readme_file_path.exists(), "README.md was not created"
    package_src = package_dir / "src"
    assert package_src.exists(), "src/ directory was not created"
    package_src = package_dir / "src" / "test_package_name"
    assert package_src.exists(), "src/test_package_name directory was not created"
    integtest_dir = package_dir / "src" / "test_package_name" / "integtest"
    assert integtest_dir.exists(), "src/test_package_name/integtest directory was not created"
    app_dir = package_dir / "src" / "test_package_name" / "apps"
    assert app_dir.exists(), "src/test_package_name/apps directory was not created"
    unit_test_dir = package_dir / "tests"
    assert unit_test_dir.exists(), "tests/ directory was not created"
    pre_commit_config_file_path = package_dir / ".pre-commit-config.yaml"
    assert pre_commit_config_file_path.exists(), ".pre-commit-config.yaml was not created"
    
    # 5. Verify file generation (e.g., check for expected sub-folders)
    assert (package_dir / "src" / "test_package_name").exists()
    assert (package_dir / "src" / "test_package_name" / "__init__.py").exists()
    assert (package_dir / "src" / "test_package_name" / "apps" / "__init__.py").exists()
    assert not (package_dir / "src" / "test_package_name" / "integtest" / "__init__.py").exists()
    
    # 6. Verify output
    output = strip_ansi(result.output)
    assert "You have successfully created your package" in output

    package_dir = tmp_path / "test-package-name"
    subprocess.check_call([sys.executable, "-m", "pip", "install", str(package_dir)])

    # 5. Run linters (Ruff is typically used in your environment)
    # This assumes ruff is installed in the test environment
    result_lint = subprocess.run(["ruff", "check", str(package_dir)], capture_output=True, text=True)
    assert result_lint.returncode == 0, f"Linting failed: {result_lint.stdout}"

    # 6. Run the applications and check output
    # Assuming your created apps are installed as console scripts or reachable via the CLI
    apps_to_test = ["test_daqpyutils_app_creation_1", "test_daqpyutils_app_creation_2"]
    
    for app in apps_to_test:
        # Execute the app; adjust the command based on how your tool names the entry points
        proc = subprocess.run([app, "--help"], capture_output=True, text=True)
        assert proc.returncode == 0, f"Here is the entry point of {app}"

    # 7. Cleanup (Optional: uninstall the package)
    subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "test-package-name"])