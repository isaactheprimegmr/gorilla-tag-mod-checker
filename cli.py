#!/usr/bin/env python3
"""
Gorilla Tag Mod Checker - CLI Interface
Enhanced command-line interface using Click
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional
from tabulate import tabulate
from colorama import Fore, Style, init

from mod_checker import ModChecker, ModStatus

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class CLIColors:
    """Color codes for CLI output"""
    SUCCESS = Fore.GREEN
    ERROR = Fore.RED
    WARNING = Fore.YELLOW
    INFO = Fore.CYAN
    RESET = Style.RESET_ALL


def print_success(message: str):
    """Print success message"""
    click.echo(f"{CLIColors.SUCCESS}✓ {message}{CLIColors.RESET}")


def print_error(message: str):
    """Print error message"""
    click.echo(f"{CLIColors.ERROR}✗ {message}{CLIColors.RESET}")


def print_warning(message: str):
    """Print warning message"""
    click.echo(f"{CLIColors.WARNING}⚠ {message}{CLIColors.RESET}")


def print_info(message: str):
    """Print info message"""
    click.echo(f"{CLIColors.INFO}ℹ {message}{CLIColors.RESET}")


def print_header(message: str):
    """Print section header"""
    click.echo(f"\n{CLIColors.INFO}{'='*60}")
    click.echo(f"{message.center(60)}")
    click.echo(f"{'='*60}{CLIColors.RESET}\n")


@click.group()
@click.version_option(version="1.0.0", prog_name="Gorilla Tag Mod Checker")
def cli():
    """
    Gorilla Tag Mod Checker - Verify and validate your mods
    
    \b
    Usage:
        gt-mod-checker check <directory>
        gt-mod-checker scan <directory>
        gt-mod-checker analyze <mod-file>
        gt-mod-checker validate <mod-file>
    """
    pass


@cli.command()
@click.argument('mod_path', type=click.Path(exists=True))
@click.option('--version', '-v', default='1.5', help='Gorilla Tag game version (default: 1.5)')
@click.option('--verbose', is_flag=True, help='Show detailed output')
def analyze(mod_path: str, version: str, verbose: bool):
    """
    Analyze a single mod file
    
    \b
    Examples:
        gt-mod-checker analyze my_mod.zip
        gt-mod-checker analyze my_mod.zip --version 1.3
        gt-mod-checker analyze my_mod.zip --verbose
    """
    print_header("Analyzing Mod")
    
    try:
        checker = ModChecker()
        mod_file = Path(mod_path)
        
        print_info(f"Analyzing: {mod_file.name}")
        print_info(f"Game Version: {version}")
        
        mod_info = checker.analyze_mod(mod_file, version)
        
        # Display results
        status_color = CLIColors.SUCCESS if mod_info.status == ModStatus.VALID.value else CLIColors.ERROR
        click.echo(f"\n{status_color}Status: {mod_info.status.upper()}{CLIColors.RESET}")
        
        click.echo(f"\nMod Information:")
        click.echo(f"  Name:            {mod_info.name}")
        click.echo(f"  Version:         {mod_info.version}")
        click.echo(f"  Author:          {mod_info.author}")
        click.echo(f"  Description:     {mod_info.description}")
        click.echo(f"  Required Game:   {mod_info.required_version}")
        click.echo(f"  File Size:       {mod_info.file_size:,} bytes")
        
        if mod_info.dependencies:
            click.echo(f"  Dependencies:")
            for dep in mod_info.dependencies:
                click.echo(f"    - {dep}")
        
        if verbose:
            click.echo(f"\nDetailed Information:")
            click.echo(f"  File Hash:       {mod_info.file_hash}")
        
        # Exit with appropriate code
        if mod_info.status == ModStatus.VALID.value:
            print_success("Mod is valid!")
            sys.exit(0)
        else:
            print_error(f"Mod validation failed: {mod_info.status}")
            sys.exit(1)
    
    except Exception as e:
        print_error(f"Error analyzing mod: {e}")
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--version', '-v', default='1.5', help='Gorilla Tag game version')
@click.option('--output', '-o', type=click.Path(), help='Output report file (JSON)')
@click.option('--format', '-f', type=click.Choice(['table', 'json', 'csv']), default='table',
              help='Output format')
def scan(directory: str, version: str, output: Optional[str], format: str):
    """
    Scan a directory for mods and validate them
    
    \b
    Examples:
        gt-mod-checker scan ./mods
        gt-mod-checker scan ./mods --version 1.3
        gt-mod-checker scan ./mods --output report.json
        gt-mod-checker scan ./mods --format json
    """
    print_header("Scanning Mod Directory")
    
    try:
        mod_dir = Path(directory)
        click.echo(f"Directory: {mod_dir.absolute()}")
        click.echo(f"Game Version: {version}\n")
        
        checker = ModChecker(str(mod_dir))
        
        # Scan directory
        with click.progressbar(length=100, label="Scanning") as bar:
            mods = checker.scan_directory(version)
            bar.update(100)
        
        if not mods:
            print_warning("No mods found in directory")
            sys.exit(0)
        
        # Generate report
        report = checker.generate_report()
        
        # Display summary
        print_header("Scan Results")
        
        summary_data = [
            ["Total Mods", report['total_mods']],
            ["Valid", f"{CLIColors.SUCCESS}{report['valid_mods']}{CLIColors.RESET}"],
            ["Invalid", f"{CLIColors.ERROR}{report['invalid_mods']}{CLIColors.RESET}"],
            ["Corrupted", f"{CLIColors.ERROR}{report['corrupted_mods']}{CLIColors.RESET}"],
            ["Incompatible", f"{CLIColors.WARNING}{report['incompatible_mods']}{CLIColors.RESET}"],
        ]
        click.echo(tabulate(summary_data, headers=["Status", "Count"], tablefmt="grid"))
        
        # Display mod details
        if mods:
            print_header("Mod Details")
            
            table_data = []
            for mod in mods:
                status_emoji = "✓" if mod.status == ModStatus.VALID.value else "✗"
                table_data.append([
                    f"{status_emoji} {mod.name}",
                    mod.version,
                    mod.author,
                    mod.status,
                    mod.required_version
                ])
            
            click.echo(tabulate(
                table_data,
                headers=["Mod Name", "Version", "Author", "Status", "Game Version"],
                tablefmt="grid"
            ))
        
        # Export report if requested
        if output:
            checker.export_report(output)
            print_success(f"Report exported to {output}")
        
        # Return appropriate exit code
        if report['invalid_mods'] > 0 or report['corrupted_mods'] > 0:
            sys.exit(1)
        else:
            print_success("All mods validated successfully!")
            sys.exit(0)
    
    except Exception as e:
        print_error(f"Error scanning directory: {e}")
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--version', '-v', default='1.5', help='Gorilla Tag game version')
@click.option('--output', '-o', type=click.Path(), help='Output report file (JSON)')
@click.option('--show-all', is_flag=True, help='Show all mod details')
def check(directory: str, version: str, output: Optional[str], show_all: bool):
    """
    Quick check of mod directory (alias for scan)
    
    \b
    Examples:
        gt-mod-checker check ./mods
        gt-mod-checker check ./mods --show-all
    """
    # Reuse scan command
    ctx = click.get_current_context()
    ctx.invoke(scan, directory=directory, version=version, output=output, format='table')


@cli.command()
@click.argument('mod_path', type=click.Path(exists=True))
@click.option('--quick', is_flag=True, help='Quick validation (metadata only)')
def validate(mod_path: str, quick: bool):
    """
    Validate a single mod file
    
    \b
    Examples:
        gt-mod-checker validate my_mod.zip
        gt-mod-checker validate my_mod.zip --quick
    """
    print_header("Validating Mod")
    
    try:
        checker = ModChecker()
        mod_file = Path(mod_path)
        
        print_info(f"Validating: {mod_file.name}")
        
        if quick:
            # Quick validation - only check metadata
            print_info("Running quick validation (metadata only)...")
            
            metadata = checker.extract_metadata(mod_file)
            if not metadata:
                print_error("No metadata found in mod file")
                sys.exit(1)
            
            is_valid, errors = checker.validate_metadata(metadata)
            
            if is_valid:
                print_success("Metadata is valid!")
                sys.exit(0)
            else:
                print_error("Metadata validation failed:")
                for error in errors:
                    print_error(f"  - {error}")
                sys.exit(1)
        else:
            # Full validation
            print_info("Running full validation...")
            
            # Check integrity
            is_valid, error = checker.check_mod_integrity(mod_file)
            if not is_valid:
                print_error(f"Integrity check failed: {error}")
                sys.exit(1)
            print_success("Integrity check passed")
            
            # Extract metadata
            metadata = checker.extract_metadata(mod_file)
            if not metadata:
                print_error("No metadata found in mod file")
                sys.exit(1)
            print_success("Metadata extracted")
            
            # Validate metadata
            is_valid, errors = checker.validate_metadata(metadata)
            if not is_valid:
                print_error("Metadata validation failed:")
                for error in errors:
                    print_error(f"  - {error}")
                sys.exit(1)
            print_success("Metadata validation passed")
            
            print_success("All validation checks passed!")
            sys.exit(0)
    
    except Exception as e:
        print_error(f"Error validating mod: {e}")
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--version', '-v', default='1.5', help='Gorilla Tag game version')
def report(directory: str, version: str):
    """
    Generate a detailed report of all mods in a directory
    
    \b
    Examples:
        gt-mod-checker report ./mods
        gt-mod-checker report ./mods --version 1.3
    """
    print_header("Generating Report")
    
    try:
        mod_dir = Path(directory)
        click.echo(f"Directory: {mod_dir.absolute()}")
        click.echo(f"Game Version: {version}\n")
        
        checker = ModChecker(str(mod_dir))
        mods = checker.scan_directory(version)
        report_data = checker.generate_report()
        
        # Export report
        report_file = mod_dir / "mod_report.json"
        checker.export_report(str(report_file))
        
        print_success(f"Report generated: {report_file}")
        
        # Display summary
        print_header("Report Summary")
        click.echo(json.dumps(report_data, indent=2))
    
    except Exception as e:
        print_error(f"Error generating report: {e}")
        sys.exit(1)


@cli.command()
@click.option('--format', '-f', type=click.Choice(['table', 'list']), default='table',
              help='Output format')
def versions(format: str):
    """
    Show supported Gorilla Tag versions
    
    \b
    Examples:
        gt-mod-checker versions
        gt-mod-checker versions --format list
    """
    print_header("Supported Gorilla Tag Versions")
    
    supported_versions = ModChecker.GORILLA_TAG_VERSIONS
    
    if format == 'list':
        for v in supported_versions:
            click.echo(f"  • {v}")
    else:
        table_data = [[v] for v in supported_versions]
        click.echo(tabulate(table_data, headers=["Version"], tablefmt="grid"))
    
    print_info(f"Total: {len(supported_versions)} versions supported")


@cli.command()
def info():
    """
    Show information about the mod checker
    """
    print_header("Gorilla Tag Mod Checker")
    
    info_data = [
        ["Version", "1.0.0"],
        ["Purpose", "Validate and check Gorilla Tag mods"],
        ["Supported Versions", f"{', '.join(ModChecker.GORILLA_TAG_VERSIONS)}"],
        ["Supported Formats", f"{', '.join(ModChecker.MOD_EXTENSIONS)}"],
    ]
    
    click.echo(tabulate(info_data, tablefmt="grid"))
    
    click.echo("\nFor help on a specific command:")
    click.echo("  gt-mod-checker <command> --help")


def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        print_warning("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
