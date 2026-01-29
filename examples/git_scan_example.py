"""
Example script demonstrating how to use the Git scanner to analyze multiple repositories.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import weekly
sys.path.append(str(Path(__file__).parent.parent))

from weekly import GitScanner

def main():
    # Configuration
    root_dir = Path.home() / "github"  # Directory containing your Git repositories
    output_dir = Path("weekly-reports")  # Where to save the reports
    since_days = 7  # Only include repositories with changes in the last X days
    
    # Create a scanner instance
    scanner = GitScanner(
        root_dir=root_dir,
        output_dir=output_dir,
        since=datetime.now() - timedelta(days=since_days),
        recursive=True,
        jobs=4
    )
    
    # Run the scan
    print(f"🔍 Scanning Git repositories in {root_dir}...")
    results = scanner.scan_all()
    
    # Print a summary
    print(f"\n✅ Scan complete! Generated reports for {len(results)} repositories.")
    print(f"📊 Summary report: {output_dir / 'summary.html'}")
    
    for result in results:
        ok_results = [r for r in result.results.values() if r is not None]
        status = "✅" if not result.error and all(getattr(r, "is_ok", True) for r in ok_results) else "❌"
        print(f"{status} {result.repo.org}/{result.repo.name}: {len(result.results)} checks")
        if result.error:
            print(f"   Error: {result.error}")
        for name, check in result.results.items():
            if check is None:
                print(f"   - {name}: (skipped)")
                continue

            status = "✓" if getattr(check, "is_ok", False) else "✗"
            print(f"   {status} {name}: {getattr(check, 'message', str(check))}")

if __name__ == "__main__":
    main()
