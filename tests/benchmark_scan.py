"""
Benchmark script for Weekly scan command.
Measures performance when scanning many repositories.
"""
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import argparse

def create_mock_repo(repo_path: Path, index: int):
    """Create a mock Git repository with some files and commits."""
    repo_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "bench@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Bench User"], cwd=repo_path, check=True)
    
    # Create some files
    (repo_path / "README.md").write_text(f"# Mock Repo {index}\nThis is mock repository number {index}.")
    (repo_path / "requirements.txt").write_text("requests==2.28.1\npytest\nblack==23.1.0")
    (repo_path / "app.py").write_text("def main():\n    print('hello')\n\nif __name__ == '__main__':\n    main()")
    
    # Initial commit
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "feat: initial commit", "-q"], cwd=repo_path, check=True)

def run_benchmark(num_repos: int, jobs: int):
    """Run the benchmark with a specified number of repositories and parallel jobs."""
    bench_dir = Path("bench_workdir")
    if bench_dir.exists():
        shutil.rmtree(bench_dir)
    bench_dir.mkdir()
    
    repos_root = bench_dir / "repos"
    output_dir = bench_dir / "reports"
    
    print(f"Creating {num_repos} mock repositories...")
    start_create = time.time()
    for i in range(num_repos):
        create_mock_repo(repos_root / f"repo_{i}", i)
    end_create = time.time()
    print(f"Created {num_repos} repositories in {end_create - start_create:.2f} seconds.")
    
    print(f"\nRunning 'weekly scan' with jobs={jobs}...")
    # Use 'python -m weekly.cli' or 'weekly' if installed
    cmd = [
        "python3", "-m", "weekly.cli", "scan",
        str(repos_root),
        "--output", str(output_dir),
        "--jobs", str(jobs),
        "--no-recursive"
    ]
    
    start_scan = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end_scan = time.time()
    
    if result.returncode != 0:
        print(f"Scan failed with return code {result.returncode}")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return
    
    scan_time = end_scan - start_scan
    print(f"Scan completed in {scan_time:.2f} seconds.")
    print(f"Average time per repository: {scan_time / num_repos:.3f} seconds.")
    
    # Cleanup
    shutil.rmtree(bench_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Weekly scan performance.")
    parser.add_argument("--repos", type=int, default=20, help="Number of repositories to create (default: 20)")
    parser.add_argument("--jobs", type=int, default=4, help="Number of parallel jobs (default: 4)")
    
    args = parser.parse_args()
    run_benchmark(args.repos, args.jobs)
