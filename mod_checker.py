#!/usr/bin/env python3
"""
Gorilla Tag Mod Checker - Core functionality for validating and checking mods
"""

import os
import json
import hashlib
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ModStatus(Enum):
    """Status codes for mod validation"""
    VALID = "valid"
    INVALID = "invalid"
    CORRUPTED = "corrupted"
    INCOMPATIBLE = "incompatible"
    MISSING_METADATA = "missing_metadata"
    UNKNOWN = "unknown"


@dataclass
class ModInfo:
    """Data class for mod information"""
    name: str
    version: str
    author: str
    description: str
    required_version: str
    dependencies: List[str]
    file_hash: str
    file_size: int
    status: str


class ModChecker:
    """Main mod checker class for Gorilla Tag mods"""
    
    GORILLA_TAG_VERSIONS = ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5"]
    MOD_EXTENSIONS = [".dll", ".so", ".dylib", ".zip"]
    REQUIRED_METADATA_FIELDS = ["name", "version", "author"]
    
    def __init__(self, mod_directory: str = "./mods"):
        """
        Initialize the mod checker
        
        Args:
            mod_directory: Path to the directory containing mods
        """
        self.mod_directory = Path(mod_directory)
        self.mods: List[ModInfo] = []
        self.validation_report: Dict = {}
        
    def check_mod_file_exists(self, mod_path: Path) -> bool:
        """Check if mod file exists"""
        return mod_path.exists()
    
    def get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def extract_metadata(self, mod_path: Path) -> Optional[Dict]:
        """Extract metadata from mod file"""
        if mod_path.suffix == ".zip":
            try:
                with zipfile.ZipFile(mod_path, 'r') as zip_ref:
                    if "mod.json" in zip_ref.namelist():
                        with zip_ref.open("mod.json") as f:
                            return json.loads(f.read().decode('utf-8'))
            except Exception as e:
                print(f"Error extracting metadata from {mod_path}: {e}")
                return None
        return None
    
    def validate_metadata(self, metadata: Dict) -> Tuple[bool, List[str]]:
        """
        Validate mod metadata
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        for field in self.REQUIRED_METADATA_FIELDS:
            if field not in metadata:
                errors.append(f"Missing required field: {field}")
        
        # Validate version format
        if "version" in metadata:
            if not self._is_valid_version(metadata["version"]):
                errors.append(f"Invalid version format: {metadata['version']}")
        
        # Validate required_version if present
        if "required_version" in metadata:
            if metadata["required_version"] not in self.GORILLA_TAG_VERSIONS:
                errors.append(f"Unsupported Gorilla Tag version: {metadata['required_version']}")
        
        # Validate dependencies if present
        if "dependencies" in metadata:
            if not isinstance(metadata["dependencies"], list):
                errors.append("Dependencies must be a list")
        
        return len(errors) == 0, errors
    
    def check_mod_integrity(self, mod_path: Path) -> Tuple[bool, str]:
        """
        Check if mod file is corrupted
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.check_mod_file_exists(mod_path):
            return False, f"Mod file not found: {mod_path}"
        
        if mod_path.suffix == ".zip":
            try:
                with zipfile.ZipFile(mod_path, 'r') as zip_ref:
                    result = zip_ref.testzip()
                    if result is not None:
                        return False, f"Corrupted file in zip: {result}"
            except zipfile.BadZipFile:
                return False, "Corrupted zip file"
            except Exception as e:
                return False, f"Error checking integrity: {e}"
        
        return True, ""
    
    def check_mod_compatibility(self, metadata: Dict, game_version: str) -> Tuple[bool, str]:
        """
        Check if mod is compatible with game version
        
        Returns:
            Tuple of (is_compatible, reason)
        """
        if "required_version" not in metadata:
            return False, "Mod metadata missing 'required_version'"
        
        required = metadata["required_version"]
        
        if game_version not in self.GORILLA_TAG_VERSIONS:
            return False, f"Unknown game version: {game_version}"
        
        if game_version != required:
            return False, f"Mod requires version {required}, but game is {game_version}"
        
        return True, "Compatible"
    
    def analyze_mod(self, mod_path: Path, game_version: str = "1.5") -> ModInfo:
        """
        Analyze a single mod file
        
        Returns:
            ModInfo object with analysis results
        """
        mod_path = Path(mod_path)
        
        # Initialize mod info
        mod_info = ModInfo(
            name="Unknown",
            version="Unknown",
            author="Unknown",
            description="No description",
            required_version="Unknown",
            dependencies=[],
            file_hash="",
            file_size=0,
            status=ModStatus.UNKNOWN.value
        )
        
        # Check if file exists
        if not self.check_mod_file_exists(mod_path):
            mod_info.status = ModStatus.INVALID.value
            return mod_info
        
        # Get file info
        mod_info.file_size = mod_path.stat().st_size
        mod_info.file_hash = self.get_file_hash(mod_path)
        
        # Check integrity
        is_valid, error = self.check_mod_integrity(mod_path)
        if not is_valid:
            mod_info.status = ModStatus.CORRUPTED.value
            return mod_info
        
        # Extract metadata
        metadata = self.extract_metadata(mod_path)
        if not metadata:
            mod_info.status = ModStatus.MISSING_METADATA.value
            return mod_info
        
        # Update mod info from metadata
        mod_info.name = metadata.get("name", "Unknown")
        mod_info.version = metadata.get("version", "Unknown")
        mod_info.author = metadata.get("author", "Unknown")
        mod_info.description = metadata.get("description", "No description")
        mod_info.required_version = metadata.get("required_version", "Unknown")
        mod_info.dependencies = metadata.get("dependencies", [])
        
        # Validate metadata
        is_valid, errors = self.validate_metadata(metadata)
        if not is_valid:
            mod_info.status = ModStatus.INVALID.value
            return mod_info
        
        # Check compatibility
        is_compatible, reason = self.check_mod_compatibility(metadata, game_version)
        if not is_compatible:
            mod_info.status = ModStatus.INCOMPATIBLE.value
            return mod_info
        
        mod_info.status = ModStatus.VALID.value
        return mod_info
    
    def scan_directory(self, game_version: str = "1.5") -> List[ModInfo]:
        """
        Scan mod directory and analyze all mods
        
        Returns:
            List of ModInfo objects
        """
        if not self.mod_directory.exists():
            print(f"Mod directory not found: {self.mod_directory}")
            return []
        
        self.mods = []
        for mod_file in self.mod_directory.iterdir():
            if mod_file.is_file() and mod_file.suffix in self.MOD_EXTENSIONS:
                mod_info = self.analyze_mod(mod_file, game_version)
                self.mods.append(mod_info)
        
        return self.mods
    
    def generate_report(self) -> Dict:
        """Generate a validation report for all scanned mods"""
        self.validation_report = {
            "total_mods": len(self.mods),
            "valid_mods": len([m for m in self.mods if m.status == ModStatus.VALID.value]),
            "invalid_mods": len([m for m in self.mods if m.status == ModStatus.INVALID.value]),
            "corrupted_mods": len([m for m in self.mods if m.status == ModStatus.CORRUPTED.value]),
            "incompatible_mods": len([m for m in self.mods if m.status == ModStatus.INCOMPATIBLE.value]),
            "mods": [asdict(m) for m in self.mods]
        }
        return self.validation_report
    
    def export_report(self, output_path: str = "mod_report.json"):
        """Export validation report to JSON file"""
        report = self.generate_report()
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report exported to {output_path}")
    
    @staticmethod
    def _is_valid_version(version_string: str) -> bool:
        """Check if version string is valid (e.g., 1.0, 1.2.3)"""
        try:
            parts = version_string.split('.')
            for part in parts:
                int(part)
            return True
        except ValueError:
            return False


def main():
    """Main entry point for the mod checker"""
    checker = ModChecker("./mods")
    
    # Scan directory
    print("Scanning mod directory...")
    mods = checker.scan_directory(game_version="1.5")
    
    # Display results
    print("\n" + "="*60)
    print("MOD CHECKER RESULTS")
    print("="*60)
    
    for mod in mods:
        print(f"\nMod: {mod.name}")
        print(f"  Version: {mod.version}")
        print(f"  Author: {mod.author}")
        print(f"  Status: {mod.status}")
        print(f"  File Size: {mod.file_size} bytes")
        print(f"  Hash: {mod.file_hash[:16]}...")
    
    # Generate and export report
    report = checker.generate_report()
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total Mods: {report['total_mods']}")
    print(f"Valid: {report['valid_mods']}")
    print(f"Invalid: {report['invalid_mods']}")
    print(f"Corrupted: {report['corrupted_mods']}")
    print(f"Incompatible: {report['incompatible_mods']}")
    
    # Export report
    checker.export_report("mod_report.json")


if __name__ == "__main__":
    main()
