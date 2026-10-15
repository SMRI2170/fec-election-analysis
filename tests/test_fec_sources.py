import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    location = ROOT / 'scripts' / name
    spec = importlib.util.spec_from_file_location(name.removesuffix('.py'), location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_official_catalog_years_and_urls():
    download = load_script('download_fec.py')
    sources = download.load_sources()
    assert sorted(sources) == [2010, 2012, 2014, 2016, 2018, 2020, 2022]
    assert sources[2022]['format'] == 'xlsx'
    assert sources[2010]['format'] == 'xls'


@pytest.mark.parametrize('extension,prefix', [
    ('xlsx', b'PK\x03\x04'),
    ('xls', bytes.fromhex('D0CF11E0A1B11AE1')),
])
def test_file_signature_accepts_valid(extension, prefix):
    load_script('download_fec.py').check_signature(prefix, extension)


@pytest.mark.parametrize('extension,unexpected', [('xlsx', b'<html>'), ('xls', b'PK\x03\x04')])
def test_file_signature_rejects_non_workbooks(extension, unexpected):
    with pytest.raises(ValueError, match='Invalid'):
        load_script('download_fec.py').check_signature(unexpected, extension)


def test_duplicate_catalog_years_rejected(tmp_path):
    download = load_script('download_fec.py')
    fixture = tmp_path / 'catalog.json'
    fixture.write_text('{"publications":[{"year":2022},{"year":2022}]}', encoding='utf-8')
    with pytest.raises(ValueError, match='Duplicate'):
        download.load_sources(fixture)


def test_audit_rejects_missing_file(tmp_path):
    audit = load_script('audit_fec_workbook.py')
    with pytest.raises(FileNotFoundError):
        audit.inspect(tmp_path / 'not-here.xlsx')
