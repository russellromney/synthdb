"""Test CLI help behavior for noun commands."""

import subprocess
import sys


def run_cli_command(args):
    """Run a CLI command and return output."""
    cmd = [sys.executable, "-m", "synthdb"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def test_noun_commands_show_help():
    """Test that noun commands without subcommands show help."""
    
    # Test main noun commands
    nouns = ["database", "table", "config", "db", "t"]
    
    for noun in nouns:
        returncode, stdout, stderr = run_cli_command([noun])
        
        # Should exit with code 0 (help is not an error)
        assert returncode == 0, f"Command 'synthdb {noun}' failed with code {returncode}"
        
        # Should show usage
        assert "Usage:" in stdout, f"No usage shown for 'synthdb {noun}'"
        assert "Commands" in stdout, f"No commands section for 'synthdb {noun}'"
        
        # Should not have error output
        assert not stderr or "Error" not in stderr, f"Unexpected error for 'synthdb {noun}': {stderr}"


def test_nested_noun_shows_help():
    """Test that nested noun commands also show help."""
    
    returncode, stdout, stderr = run_cli_command(["table", "add"])
    
    assert returncode == 0
    assert "Usage:" in stdout
    assert "column" in stdout  # Should show the column subcommand
    

def test_help_flag_still_works():
    """Test that explicit --help flag still works."""
    
    # Test with explicit help flag
    nouns = ["database", "table", "config"]
    
    for noun in nouns:
        returncode1, stdout1, _ = run_cli_command([noun])
        returncode2, stdout2, _ = run_cli_command([noun, "--help"])
        
        # Both should succeed
        assert returncode1 == 0
        assert returncode2 == 0
        
        # Output should be similar (both show help)
        assert "Usage:" in stdout1
        assert "Usage:" in stdout2


def test_main_command_shows_help():
    """Test that main synthdb command without args shows help."""
    
    returncode, stdout, stderr = run_cli_command([])
    
    # Should exit with code 0 (help is not an error)
    assert returncode == 0
    assert "Usage:" in stdout
    assert "Commands" in stdout
    assert "database" in stdout  # Should list the noun commands
    assert "table" in stdout


if __name__ == "__main__":
    test_noun_commands_show_help()
    test_nested_noun_shows_help()
    test_help_flag_still_works()
    test_main_command_shows_help()
    print("✅ All CLI help tests passed!")