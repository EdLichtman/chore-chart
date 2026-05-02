"""Tests for the visual validation loop added to generate_almanac.py."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from generate_almanac import all_rules_pass

def test_all_rules_pass_when_all_pass():
    results = {"rules": [
        {"id": 1, "status": "PASS"},
        {"id": 2, "status": "PASS"},
    ]}
    assert all_rules_pass(results) is True

def test_all_rules_pass_returns_false_on_any_fail():
    results = {"rules": [
        {"id": 1, "status": "PASS"},
        {"id": 2, "status": "FAIL"},
    ]}
    assert all_rules_pass(results) is False

def test_all_rules_pass_treats_uncertain_as_passing():
    results = {"rules": [
        {"id": 1, "status": "PASS"},
        {"id": 7, "status": "UNCERTAIN"},
    ]}
    assert all_rules_pass(results) is True

def test_all_rules_pass_handles_empty():
    assert all_rules_pass({"rules": []}) is True
