import re
import subprocess
import sys
from pathlib import Path

from click.testing import CliRunner, Result

from daqpyutils.apps.create_python_dunedaq_package import (
    main as create_python_dunedaq_package,
)

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")
runner = CliRunner()
test_package_name = "test_daqpyutils_package"


def strip_ansi(text: str) -> str:
    r"""
    Strip ANSI escape sequences, newlines and carriage returns.

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


def test_strip_ansi() -> None:
    """Test the strip_ansi function."""
    sample_input = "\x1b[31mHello\x1b[0m\nWorld"
    assert strip_ansi(sample_input) == "HelloWorld"


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
    Test function create_a_package_and_validate.

    Test that a test repository can be generated, is pip installable, has runnable
    applications, and that it passes all the checks.
    """
    runner = CliRunner()
    package_name = "daqpyutilsUnitTestPackage"

    # EVERYTHING goes inside this context block
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # 1. Setup paths relative to the isolation sandbox
        requirements_file = Path("requirements.txt")
        requirements_file.write_text("grpcio\n")

        application_file = Path("apps.txt")
        application_file.write_text("test-daqpyutils-app-creation-1\n")

        # 2. Invoke the CLI command
        result = runner.invoke(
            create_python_dunedaq_package,
            [
                package_name,
                "-l",
                "info",
                "-r",
                "click",
                "-rf",
                str(requirements_file),
                "-a",
                "test-daqpyutils-app-creation-2",
                "-af",
                str(application_file),
                "-p",
                "Test of the package creation",
                "-s",
            ],
            obj={"root_path": tmp_path},
        )

        # 3. Assert CLI success (must be inside to print output properly on failure)
        assert result.exit_code == 0, f"CLI crashed: {result.output}"

        # 4. Verify directory structure (Uses relative path 'package_name' safely here)
        package_dir = Path(package_name)
        assert package_dir.exists(), "Package directory was not created"

        pyproject_toml_file_path = package_dir / "pyproject.toml"
        assert pyproject_toml_file_path.exists(), "pyproject.toml was not created"

        gitignore_file_path = package_dir / ".gitignore"
        assert gitignore_file_path.exists(), ".gitignore was not created"

        github_dir = package_dir / ".github"
        assert github_dir.exists(), ".github directory was not created"

        github_workflow_dir = github_dir / "workflows"
        assert github_workflow_dir.exists(), (
            ".github/workflows directory was not created"
        )

        pull_request_template_file_path = github_dir / "pull_request_template.md"
        assert pull_request_template_file_path.exists(), (
            "pull_request_template.md was not created"
        )

        lint_workflow_file_path = github_workflow_dir / "lint.yml"
        assert lint_workflow_file_path.exists(), "lint.yml was not created"

        pytest_workflow_file_path = github_workflow_dir / "pytest.yml"
        assert pytest_workflow_file_path.exists(), "pytest.yml was not created"

        track_new_issues_workflow_file_path = (
            github_workflow_dir / "track_new_issues.yml"
        )
        assert track_new_issues_workflow_file_path.exists(), (
            "track_new_issues.yml was not created"
        )

        track_new_prs_workflow_file_path = github_workflow_dir / "track_new_prs.yml"
        assert track_new_prs_workflow_file_path.exists(), (
            "track_new_prs.yml was not created"
        )

        readme_file_path = package_dir / "docs" / "README.md"
        assert readme_file_path.exists(), "README.md was not created"

        package_src = package_dir / "src"
        assert package_src.exists(), "src/ directory was not created"

        package_src_named = package_src / package_name
        assert package_src_named.exists(), (
            f"src/{package_name} directory was not created"
        )

        integtest_dir = package_src_named / "integtest"
        assert integtest_dir.exists(), (
            f"src/{package_name}/integtest directory was not created"
        )

        app_dir = package_src_named / "apps"
        assert app_dir.exists(), f"src/{package_name}/apps directory was not created"

        unit_test_dir = package_dir / "tests"
        assert unit_test_dir.exists(), "tests/ directory was not created"

        pre_commit_config_file_path = package_dir / ".pre-commit-config.yaml"
        assert pre_commit_config_file_path.exists(), (
            ".pre-commit-config.yaml was not created"
        )

        # 5. Verify file generation
        assert (package_dir / "src" / package_name / "__init__.py").exists()
        assert (package_dir / "src" / package_name / "apps" / "__init__.py").exists()

        # 6. Verify output string
        output = strip_ansi(result.output)
        assert "You have successfully created your package" in output

        # 7. Pip install using the resolved absolute path of the sandbox directory
        absolute_package_dir = package_dir.resolve()
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", str(absolute_package_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            raise

        # 5. Run linters (Ruff)
        result_lint = subprocess.run(
            ["ruff", "check", str(package_dir.resolve())],
            capture_output=True,
            text=True,
        )
        assert result_lint.returncode == 0, (
            "Linting failed:\n"
            "STDOUT:\n{result_lint.stdout}\n"
            "STDERR:\n{result_lint.stderr}"
        )

        # 6. Run the applications and check output
        # App names match the exact strings used in your CLI invocation inputs
        apps_to_test = [
            "test-daqpyutils-app-creation-1",
            "test-daqpyutils-app-creation-2",
        ]

        for app in apps_to_test:
            try:
                proc = subprocess.run([app, "--help"], capture_output=True, text=True)
                assert proc.returncode == 0, (
                    f"App {app} failed to execute with --help. Output:\n{proc.stderr}"
                )
            except subprocess.CalledProcessError:
                raise
            except FileNotFoundError as e:
                print(f"STDOUT:\n{proc.stdout}")
                print(f"STDERR:\n{proc.stderr}")
                new_err_str = f"App {app} was not found in PATH."
                raise AssertionError(new_err_str) from e

        # 7. Cleanup (Uninstall the package cleanly using its real package name)
        # Your target package name variable is 'package_name'
        subprocess.check_call(
            [sys.executable, "-m", "pip", "uninstall", "-y", package_name]
        )
