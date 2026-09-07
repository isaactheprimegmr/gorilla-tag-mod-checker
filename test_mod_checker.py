#!/usr/bin/env python3
"""
Unit tests for the Gorilla Tag Mod Checker
"""

import unittest
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from mod_checker import ModChecker, ModStatus, ModInfo


class TestModChecker(unittest.TestCase):
    """Test cases for ModChecker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mod_directory = Path(self.temp_dir.name)
        self.checker = ModChecker(str(self.mod_directory))
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()
    
    def create_test_mod_zip(self, filename: str, metadata: dict) -> Path:
        """Helper to create a test mod ZIP file"""
        mod_path = self.mod_directory / filename
        with zipfile.ZipFile(mod_path, 'w') as zf:
            zf.writestr('mod.json', json.dumps(metadata))
            zf.writestr('dummy.txt', 'test content')
        return mod_path
    
    def create_corrupted_zip(self, filename: str) -> Path:
        """Helper to create a corrupted ZIP file"""
        mod_path = self.mod_directory / filename
        with open(mod_path, 'wb') as f:
            f.write(b'PK\x03\x04' + b'\x00' * 100)  # Invalid ZIP structure
        return mod_path


class TestFileOperations(TestModChecker):
    """Tests for file-related operations"""
    
    def test_check_mod_file_exists_true(self):
        """Test detecting existing mod file"""
        mod_path = self.create_test_mod_zip('test.zip', {'name': 'test'})
        self.assertTrue(self.checker.check_mod_file_exists(mod_path))
    
    def test_check_mod_file_exists_false(self):
        """Test detecting missing mod file"""
        non_existent = self.mod_directory / 'non_existent.zip'
        self.assertFalse(self.checker.check_mod_file_exists(non_existent))
    
    def test_get_file_hash(self):
        """Test file hash calculation"""
        mod_path = self.create_test_mod_zip('test.zip', {'name': 'test'})
        hash1 = self.checker.get_file_hash(mod_path)
        hash2 = self.checker.get_file_hash(mod_path)
        
        # Same file should produce same hash
        self.assertEqual(hash1, hash2)
        # Hash should be 64 characters (SHA256 hex)
        self.assertEqual(len(hash1), 64)
    
    def test_get_file_hash_different_files(self):
        """Test different files produce different hashes"""
        mod1 = self.create_test_mod_zip('test1.zip', {'name': 'mod1'})
        mod2 = self.create_test_mod_zip('test2.zip', {'name': 'mod2'})
        
        hash1 = self.checker.get_file_hash(mod1)
        hash2 = self.checker.get_file_hash(mod2)
        
        self.assertNotEqual(hash1, hash2)


class TestMetadataExtraction(TestModChecker):
    """Tests for metadata extraction"""
    
    def test_extract_metadata_valid(self):
        """Test extracting valid metadata"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'TestAuthor',
            'required_version': '1.5'
        }
        mod_path = self.create_test_mod_zip('test.zip', metadata)
        extracted = self.checker.extract_metadata(mod_path)
        
        self.assertEqual(extracted['name'], 'TestMod')
        self.assertEqual(extracted['version'], '1.0')
        self.assertEqual(extracted['author'], 'TestAuthor')
    
    def test_extract_metadata_no_mod_json(self):
        """Test extracting metadata from ZIP without mod.json"""
        mod_path = self.mod_directory / 'test.zip'
        with zipfile.ZipFile(mod_path, 'w') as zf:
            zf.writestr('dummy.txt', 'no metadata')
        
        extracted = self.checker.extract_metadata(mod_path)
        self.assertIsNone(extracted)
    
    def test_extract_metadata_non_zip(self):
        """Test extracting metadata from non-ZIP file"""
        mod_path = self.mod_directory / 'test.dll'
        mod_path.write_text('not a zip file')
        
        extracted = self.checker.extract_metadata(mod_path)
        self.assertIsNone(extracted)


class TestMetadataValidation(TestModChecker):
    """Tests for metadata validation"""
    
    def test_validate_metadata_valid(self):
        """Test validating correct metadata"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'Author'
        }
        is_valid, errors = self.checker.validate_metadata(metadata)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_metadata_missing_name(self):
        """Test validation fails without name"""
        metadata = {
            'version': '1.0',
            'author': 'Author'
        }
        is_valid, errors = self.checker.validate_metadata(metadata)
        
        self.assertFalse(is_valid)
        self.assertIn('Missing required field: name', errors)
    
    def test_validate_metadata_missing_version(self):
        """Test validation fails without version"""
        metadata = {
            'name': 'TestMod',
            'author': 'Author'
        }
        is_valid, errors = self.checker.validate_metadata(metadata)
        
        self.assertFalse(is_valid)
        self.assertIn('Missing required field: version', errors)
    
    def test_validate_metadata_missing_author(self):
        """Test validation fails without author"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0'
        }
        is_valid, errors = self.checker.validate_metadata(metadata)
        
        self.assertFalse(is_valid)
        self.assertIn('Missing required field: author', errors)
    
    def test_validate_metadata_invalid_version_format(self):
        """Test validation fails with invalid version"""
        metadata = {
            'name': 'TestMod',
            'version': 'invalid_version',
            'author': 'Author'
        }
        is_valid, errors = self.checker.validate_metadata(metadata)
        
        self.assertFalse(is_valid)
        self.assertIn('Invalid version format: invalid_version', errors)
    
    def test_validate_metadata_invalid_required_version(self):
        """Test validation fails with unsupported game version"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'Author',
            'required_version': '99.0'
        }
        is_valid, errors = self.checker.validate_metadata(metadata)
        
        self.assertFalse(is_valid)
        self.assertIn('Unsupported Gorilla Tag version: 99.0', errors)
    
    def test_validate_metadata_invalid_dependencies(self):
        """Test validation fails with invalid dependencies"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'Author',
            'dependencies': 'not_a_list'
        }
        is_valid, errors = self.checker.validate_metadata(metadata)
        
        self.assertFalse(is_valid)
        self.assertIn('Dependencies must be a list', errors)


class TestIntegrityChecking(TestModChecker):
    """Tests for file integrity checking"""
    
    def test_check_integrity_valid_zip(self):
        """Test integrity check on valid ZIP"""
        metadata = {'name': 'TestMod', 'version': '1.0', 'author': 'Author'}
        mod_path = self.create_test_mod_zip('test.zip', metadata)
        
        is_valid, error = self.checker.check_mod_integrity(mod_path)
        
        self.assertTrue(is_valid)
        self.assertEqual(error, '')
    
    def test_check_integrity_corrupted_zip(self):
        """Test integrity check on corrupted ZIP"""
        mod_path = self.create_corrupted_zip('corrupted.zip')
        
        is_valid, error = self.checker.check_mod_integrity(mod_path)
        
        self.assertFalse(is_valid)
        self.assertIn('Corrupted', error)
    
    def test_check_integrity_file_not_found(self):
        """Test integrity check on non-existent file"""
        mod_path = self.mod_directory / 'non_existent.zip'
        
        is_valid, error = self.checker.check_mod_integrity(mod_path)
        
        self.assertFalse(is_valid)
        self.assertIn('not found', error)


class TestCompatibilityChecking(TestModChecker):
    """Tests for compatibility checking"""
    
    def test_check_compatibility_compatible(self):
        """Test compatible mod"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'Author',
            'required_version': '1.5'
        }
        is_compatible, reason = self.checker.check_mod_compatibility(metadata, '1.5')
        
        self.assertTrue(is_compatible)
        self.assertEqual(reason, 'Compatible')
    
    def test_check_compatibility_incompatible_version(self):
        """Test incompatible mod version"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'Author',
            'required_version': '1.0'
        }
        is_compatible, reason = self.checker.check_mod_compatibility(metadata, '1.5')
        
        self.assertFalse(is_compatible)
        self.assertIn('requires version 1.0', reason)
    
    def test_check_compatibility_missing_required_version(self):
        """Test mod without required_version"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'Author'
        }
        is_compatible, reason = self.checker.check_mod_compatibility(metadata, '1.5')
        
        self.assertFalse(is_compatible)
        self.assertIn('missing', reason.lower())
    
    def test_check_compatibility_unknown_game_version(self):
        """Test with unknown game version"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'Author',
            'required_version': '1.5'
        }
        is_compatible, reason = self.checker.check_mod_compatibility(metadata, '99.0')
        
        self.assertFalse(is_compatible)
        self.assertIn('Unknown game version', reason)


class TestModAnalysis(TestModChecker):
    """Tests for complete mod analysis"""
    
    def test_analyze_mod_valid(self):
        """Test analyzing a valid mod"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'TestAuthor',
            'description': 'A test mod',
            'required_version': '1.5',
            'dependencies': []
        }
        mod_path = self.create_test_mod_zip('test.zip', metadata)
        
        mod_info = self.checker.analyze_mod(mod_path, '1.5')
        
        self.assertEqual(mod_info.status, ModStatus.VALID.value)
        self.assertEqual(mod_info.name, 'TestMod')
        self.assertEqual(mod_info.version, '1.0')
        self.assertEqual(mod_info.author, 'TestAuthor')
    
    def test_analyze_mod_corrupted(self):
        """Test analyzing a corrupted mod"""
        mod_path = self.create_corrupted_zip('corrupted.zip')
        
        mod_info = self.checker.analyze_mod(mod_path, '1.5')
        
        self.assertEqual(mod_info.status, ModStatus.CORRUPTED.value)
    
    def test_analyze_mod_missing_metadata(self):
        """Test analyzing mod without metadata"""
        mod_path = self.mod_directory / 'test.zip'
        with zipfile.ZipFile(mod_path, 'w') as zf:
            zf.writestr('dummy.txt', 'no metadata')
        
        mod_info = self.checker.analyze_mod(mod_path, '1.5')
        
        self.assertEqual(mod_info.status, ModStatus.MISSING_METADATA.value)
    
    def test_analyze_mod_invalid_metadata(self):
        """Test analyzing mod with invalid metadata"""
        metadata = {
            'version': '1.0'
            # Missing required fields
        }
        mod_path = self.create_test_mod_zip('test.zip', metadata)
        
        mod_info = self.checker.analyze_mod(mod_path, '1.5')
        
        self.assertEqual(mod_info.status, ModStatus.INVALID.value)
    
    def test_analyze_mod_incompatible(self):
        """Test analyzing incompatible mod"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'Author',
            'required_version': '1.0'
        }
        mod_path = self.create_test_mod_zip('test.zip', metadata)
        
        mod_info = self.checker.analyze_mod(mod_path, '1.5')
        
        self.assertEqual(mod_info.status, ModStatus.INCOMPATIBLE.value)
    
    def test_analyze_mod_file_not_found(self):
        """Test analyzing non-existent mod"""
        mod_path = self.mod_directory / 'non_existent.zip'
        
        mod_info = self.checker.analyze_mod(mod_path, '1.5')
        
        self.assertEqual(mod_info.status, ModStatus.INVALID.value)


class TestDirectoryScanning(TestModChecker):
    """Tests for scanning mod directories"""
    
    def test_scan_directory_empty(self):
        """Test scanning empty directory"""
        mods = self.checker.scan_directory()
        
        self.assertEqual(len(mods), 0)
    
    def test_scan_directory_single_mod(self):
        """Test scanning directory with one mod"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'Author',
            'required_version': '1.5'
        }
        self.create_test_mod_zip('test.zip', metadata)
        
        mods = self.checker.scan_directory('1.5')
        
        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0].name, 'TestMod')
    
    def test_scan_directory_multiple_mods(self):
        """Test scanning directory with multiple mods"""
        for i in range(3):
            metadata = {
                'name': f'TestMod{i}',
                'version': '1.0',
                'author': 'Author',
                'required_version': '1.5'
            }
            self.create_test_mod_zip(f'test{i}.zip', metadata)
        
        mods = self.checker.scan_directory('1.5')
        
        self.assertEqual(len(mods), 3)
    
    def test_scan_directory_mixed_validity(self):
        """Test scanning directory with valid and invalid mods"""
        # Valid mod
        valid_metadata = {
            'name': 'ValidMod',
            'version': '1.0',
            'author': 'Author',
            'required_version': '1.5'
        }
        self.create_test_mod_zip('valid.zip', valid_metadata)
        
        # Invalid mod (missing metadata)
        invalid_path = self.mod_directory / 'invalid.zip'
        with zipfile.ZipFile(invalid_path, 'w') as zf:
            zf.writestr('dummy.txt', 'no metadata')
        
        mods = self.checker.scan_directory('1.5')
        
        self.assertEqual(len(mods), 2)
        valid_count = sum(1 for m in mods if m.status == ModStatus.VALID.value)
        invalid_count = sum(1 for m in mods if m.status != ModStatus.VALID.value)
        self.assertEqual(valid_count, 1)
        self.assertEqual(invalid_count, 1)


class TestReportGeneration(TestModChecker):
    """Tests for report generation"""
    
    def test_generate_report_empty(self):
        """Test generating report with no mods"""
        report = self.checker.generate_report()
        
        self.assertEqual(report['total_mods'], 0)
        self.assertEqual(report['valid_mods'], 0)
        self.assertEqual(report['invalid_mods'], 0)
        self.assertEqual(report['corrupted_mods'], 0)
        self.assertEqual(report['incompatible_mods'], 0)
    
    def test_generate_report_with_mods(self):
        """Test generating report with mods"""
        # Create valid mod
        valid_metadata = {
            'name': 'ValidMod',
            'version': '1.0',
            'author': 'Author',
            'required_version': '1.5'
        }
        self.create_test_mod_zip('valid.zip', valid_metadata)
        
        # Create invalid mod
        invalid_path = self.mod_directory / 'invalid.zip'
        with zipfile.ZipFile(invalid_path, 'w') as zf:
            zf.writestr('dummy.txt', 'no metadata')
        
        self.checker.scan_directory('1.5')
        report = self.checker.generate_report()
        
        self.assertEqual(report['total_mods'], 2)
        self.assertEqual(report['valid_mods'], 1)
        self.assertGreater(report['invalid_mods'] + report['corrupted_mods'], 0)
    
    def test_export_report(self):
        """Test exporting report to file"""
        metadata = {
            'name': 'TestMod',
            'version': '1.0',
            'author': 'Author',
            'required_version': '1.5'
        }
        self.create_test_mod_zip('test.zip', metadata)
        
        self.checker.scan_directory('1.5')
        report_path = self.mod_directory / 'report.json'
        self.checker.export_report(str(report_path))
        
        self.assertTrue(report_path.exists())
        
        with open(report_path) as f:
            report = json.load(f)
        
        self.assertEqual(report['total_mods'], 1)
        self.assertEqual(report['valid_mods'], 1)


class TestVersionValidation(TestModChecker):
    """Tests for version string validation"""
    
    def test_is_valid_version_simple(self):
        """Test simple version format"""
        self.assertTrue(self.checker._is_valid_version('1.0'))
    
    def test_is_valid_version_complex(self):
        """Test complex version format"""
        self.assertTrue(self.checker._is_valid_version('1.2.3'))
    
    def test_is_valid_version_single_number(self):
        """Test single number version"""
        self.assertTrue(self.checker._is_valid_version('1'))
    
    def test_is_valid_version_invalid(self):
        """Test invalid version format"""
        self.assertFalse(self.checker._is_valid_version('1.0.a'))
    
    def test_is_valid_version_empty(self):
        """Test empty version"""
        self.assertFalse(self.checker._is_valid_version(''))


if __name__ == '__main__':
    unittest.main()
