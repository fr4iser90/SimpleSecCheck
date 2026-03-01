"""
Central path setup for SimpleSecCheck
Sets up sys.path to include processors and core modules
"""
import os
import sys


def setup_paths():
    """
    Setup sys.path to include processors and core modules
    Works from any location in the project
    Central path management - no other file should calculate paths!
    """
    # Add Docker paths first (if exists) - needed for Docker containers
    sys.path.insert(0, "/project/src")
    sys.path.insert(0, "/SimpleSecCheck")
    sys.path.insert(0, "/SimpleSecCheck/scripts")
    
    # Get the src/ directory (this file is in src/core/)
    SRC_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # Add processors and core to path
    PROCESSORS_DIR = os.path.join(SRC_DIR, "processors")
    CORE_DIR = os.path.join(SRC_DIR, "core")
    
    sys.path.insert(0, SRC_DIR)
    sys.path.insert(0, PROCESSORS_DIR)
    sys.path.insert(0, CORE_DIR)
