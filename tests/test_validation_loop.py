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

from unittest.mock import patch, MagicMock
from generate_almanac import find_libreoffice, convert_to_image
import os

def test_find_libreoffice_returns_known_path():
    path = find_libreoffice()
    assert path.endswith("soffice.exe")
    assert os.path.exists(path)

def test_convert_to_image_returns_png_paths(tmp_path):
    fake_docx = tmp_path / "test.docx"
    fake_docx.write_bytes(b"fake")
    fake_pdf = tmp_path / "test.pdf"
    fake_pdf.write_bytes(b"fake")

    mock_page = MagicMock()
    mock_pix = MagicMock()
    mock_pix.save = MagicMock()
    mock_page.get_pixmap.return_value = mock_pix

    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
    mock_doc.__len__ = MagicMock(return_value=1)

    with patch("generate_almanac.subprocess.run") as mock_run, \
         patch("generate_almanac.fitz.open", return_value=mock_doc):
        mock_run.return_value = MagicMock(returncode=0)
        result = convert_to_image(str(fake_docx), str(tmp_path))

    assert len(result) == 1
    assert result[0].endswith(".png")

from generate_almanac import validate_image
import json

def test_validate_image_parses_json_from_claude(tmp_path):
    fake_img = tmp_path / "page_1.png"
    fake_img.write_bytes(b"fake")
    checklist = tmp_path / "checklist.md"
    checklist.write_text("## Rule 1: test rule\n- PASS condition: visible\n")

    expected = {"rules": [{"id": 1, "name": "test rule", "status": "PASS", "reason": "visible"}]}
    mock_output = json.dumps({
        "type": "result",
        "subtype": "success",
        "result": json.dumps(expected)
    })

    with patch("generate_almanac.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")
        result = validate_image([str(fake_img)], str(checklist))

    assert result["rules"][0]["status"] == "PASS"

def test_validate_image_strips_markdown_fences(tmp_path):
    fake_img = tmp_path / "page_1.png"
    fake_img.write_bytes(b"fake")
    checklist = tmp_path / "checklist.md"
    checklist.write_text("rule")

    inner = {"rules": [{"id": 1, "status": "PASS", "name": "r", "reason": "ok"}]}
    fenced = f"```json\n{json.dumps(inner)}\n```"
    mock_output = json.dumps({
        "type": "result", "subtype": "success", "result": fenced
    })

    with patch("generate_almanac.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output, stderr="")
        result = validate_image([str(fake_img)], str(checklist))

    assert result["rules"][0]["id"] == 1
