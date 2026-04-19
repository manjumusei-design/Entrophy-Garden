# test_cli_output.py
"""Test the cli_output utility function like human_size, logging and banner"""
from entropygarden import cli_output


def test_human_size_bytes():
    """Bytes under 1024 should show as B"""
    assert cli_output.human_size(0) == "0 B"
    assert cli_output.human_size(512) == "512 B"
    assert cli_output.human_size (1023) == "1023 B"
    

def test_human_size_kilobytes():
    """Values 1024 to 1 MB should show as KB"""
    assert cli_output.human_size(1024) == "1.0 KB"
    assert cli_output.human_size(1536) == "1.5 KB"


def test_human_size_megabytes():
    """Values 1MB to 1 GB should show as MB"""
    assert cli_output.human_size(1024**2) == "1.0 MB"
    
    
def test_human_size_gigabytes():
    """Values over 1GB should show as GB"""
    assert cli_output.human_size(1024 ** 3) == "1.0 GB"