"""
Git scanner report generation module for Weekly.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict, field

class CheckResult:
    """Represents the result of a single check."""
    
    def __init__(
        self,
        name: str,
        description: str,
        is_ok: bool,
        message: str,
        details: Optional[Dict] = None,
        next_steps: Optional[List[str]] = None,
        severity: str = "medium",
        metadata: Optional[Dict] = None
    ):
        """Initialize a check result.
        
        Args:
            name: Name of the check
            description: Description of the check
            is_ok: Whether the check passed
            message: Result message
            details: Optional detailed results
            next_steps: List of suggested next steps
            severity: Severity level (low, medium, high)
            metadata: Optional metadata dictionary
        """
        self.name = name
        self.description = description
        self.is_ok = is_ok
        self.message = message
        self.details = details
        self.next_steps = next_steps or []
        self.severity = severity
        self.metadata = metadata or {}

@dataclass
class RepoInfo:
    """Repository information for reports."""
    name: str
    org: str = ""
    path: str = ""
    branch: str = "main"
    remote_url: str = ""
    last_commit_date: Optional[str] = None
    has_errors: bool = False

class GitReportGenerator:
    """Generates reports for Git repository scans."""
    
    @staticmethod
    def generate_llm_report(
        results: Dict[str, CheckResult],
        repo_info: RepoInfo,
        output_path: Union[str, Path],
        title: str = "Weekly Report - LLM Format"
    ) -> None:
        """Generate an LLM-optimized Markdown report for code fixing.
        
        Args:
            results: Dictionary of check results
            repo_info: Repository information
            output_path: Path to save the Markdown report
            title: Report title
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate LLM-optimized Markdown content
        markdown_lines = []
        
        # LLM-friendly header with clear instructions
        markdown_lines.append(f"# {title} - LLM Code Fixing Report")
        markdown_lines.append("")
        markdown_lines.append("## 🤖 LLM Instructions")
        markdown_lines.append("")
        markdown_lines.append("**Your Role:** You are a Python code quality expert helping to fix issues systematically.")
        markdown_lines.append("**Your Task:** Analyze the report below and provide a step-by-step fix plan.")
        markdown_lines.append("**Priority Order:** Critical errors → Bulk formatting → Detailed fixes")
        markdown_lines.append("")
        markdown_lines.append("---")
        markdown_lines.append("")
        markdown_lines.append("## 📁 Repository Context")
        markdown_lines.append("")
        markdown_lines.append(f"- **Project:** {repo_info.org}/{repo_info.name}")
        markdown_lines.append(f"- **Location:** `{repo_info.path}`")
        markdown_lines.append(f"- **Branch:** {repo_info.branch}")
        markdown_lines.append(f"- **Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        markdown_lines.append("")
        markdown_lines.append("---")
        markdown_lines.append("")
        
        # Collect all issues by file
        issues_by_file = {}
        bulk_issues = {}
        
        for name, result in results.items():
            if result.metadata and 'issues_data' in result.metadata:
                issues_data = result.metadata['issues_data']
                
                for tool, issues in issues_data.items():
                    if tool not in bulk_issues:
                        bulk_issues[tool] = []
                    
                    # Group issues by file
                    for issue in issues:
                        file_path = issue['file']
                        if file_path not in issues_by_file:
                            issues_by_file[file_path] = []
                        issues_by_file[file_path].append({
                            **issue,
                            'tool': tool
                        })
                        bulk_issues[tool].append(issue)
        
        # Priority 1: Critical errors (non-formatting)
        markdown_lines.append("## 🚨 Priority 1: Critical Errors")
        markdown_lines.append("")
        markdown_lines.append("*These errors must be fixed manually before formatting.*")
        markdown_lines.append("")
        critical_found = False
        critical_count = 0
        
        for file_path in sorted(issues_by_file.keys()):
            file_issues = issues_by_file[file_path]
            critical_issues = [i for i in file_issues if i['tool'] != 'black' and i['code'] != 'BLK100']
            
            if critical_issues:
                critical_found = True
                critical_count += len(critical_issues)
                markdown_lines.append(f"### 📄 File: `{file_path}`")
                markdown_lines.append("")
                
                for issue in sorted(critical_issues, key=lambda x: x['line']):
                    markdown_lines.append(f"**Line {issue['line']}:** `{issue['code']}` - {issue['message']}")
                    markdown_lines.append(f"- **Tool:** {issue['tool']}")
                    markdown_lines.append(f"- **Command:** `{issue['tool'].lower()} {file_path}`")
                    markdown_lines.append("")
        
        if not critical_found:
            markdown_lines.append("✅ **No critical errors found.**")
            markdown_lines.append("")
        else:
            markdown_lines.append(f"**Total Critical Errors:** {critical_count}")
            markdown_lines.append("")
        
        # Priority 2: Bulk formatting issues
        markdown_lines.append("## 📝 Priority 2: Bulk Formatting Issues")
        markdown_lines.append("")
        markdown_lines.append("*These can be fixed automatically with a single command.*")
        markdown_lines.append("")
        
        for tool, issues in bulk_issues.items():
            if tool.lower() in ['black', 'isort'] and len(issues) > 5:
                tool_name = tool.upper()
                file_count = len(issues)
                
                markdown_lines.append(f"### {tool_name} Formatting ({file_count} files)")
                markdown_lines.append("")
                markdown_lines.append("**Affected Files (showing first 10):**")
                for issue in issues[:10]:
                    rel_path = issue['file'].replace('/home/tom/github/exef-pl/app/', '')
                    markdown_lines.append(f"- `{rel_path}`")
                if len(issues) > 10:
                    markdown_lines.append(f"- ... and {len(issues) - 10} more files")
                markdown_lines.append("")
                markdown_lines.append("**Fix Command:**")
                markdown_lines.append("```bash")
                markdown_lines.append(f"cd {repo_info.path} && {tool.lower()} .")
                markdown_lines.append("```")
                markdown_lines.append("")
                
                # Add safety note
                if tool.lower() == 'black':
                    markdown_lines.append("⚠️ **Note:** Black will reformat your code. Review changes before committing.")
                    markdown_lines.append("")
        
        # Priority 3: Detailed issues by file (limited)
        markdown_lines.append("## 📋 Priority 3: Individual File Issues")
        markdown_lines.append("")
        markdown_lines.append("*These require individual attention per file.*")
        markdown_lines.append("")
        markdown_lines.append(f"*Showing first 20 files with non-formatting issues*")
        markdown_lines.append("")
        
        file_count = 0
        for file_path in sorted(issues_by_file.keys()):
            if file_count >= 20:
                break
                
            file_issues = issues_by_file[file_path]
            # Skip if only has formatting issues
            if all(i['tool'].lower() in ['black', 'isort'] for i in file_issues):
                continue
                
            file_count += 1
            rel_path = file_path.replace('/home/tom/github/exef-pl/app/', '')
            markdown_lines.append(f"### 📄 File: `{rel_path}`")
            markdown_lines.append("")
            
            # Group issues by line for better context
            issues_by_line = {}
            for issue in file_issues:
                if issue['tool'].lower() in ['black', 'isort']:
                    continue
                line = issue['line']
                if line not in issues_by_line:
                    issues_by_line[line] = []
                issues_by_line[line].append(issue)
            
            if issues_by_line:
                for line in sorted(issues_by_line.keys()):
                    line_issues = issues_by_line[line]
                    for issue in line_issues:
                        markdown_lines.append(f"**Line {line}:** `{issue['code']}` - {issue['message']}")
                        markdown_lines.append(f"- **Tool:** {issue['tool']}")
                        markdown_lines.append("")
            else:
                markdown_lines.append("*Only formatting issues (see Priority 2)*")
                markdown_lines.append("")
        
        if file_count == 0:
            markdown_lines.append("✅ **No individual file issues found beyond formatting.**")
            markdown_lines.append("")
        
        # Summary and next steps
        markdown_lines.append("---")
        markdown_lines.append("")
        markdown_lines.append("## 📊 Issue Summary")
        markdown_lines.append("")
        total_issues = sum(len(issues) for issues in bulk_issues.values())
        critical_issues = sum(len([i for i in issues if i.get('tool', '').lower() not in ['black', 'isort']]) for issues in bulk_issues.values())
        formatting_issues = total_issues - critical_issues
        
        markdown_lines.append(f"- **Total Issues:** {total_issues}")
        markdown_lines.append(f"- **Critical Errors:** {critical_issues}")
        markdown_lines.append(f"- **Formatting Issues:** {formatting_issues}")
        markdown_lines.append(f"- **Files Affected:** {len(issues_by_file)}")
        markdown_lines.append("")
        
        markdown_lines.append("## 🎯 LLM Action Plan")
        markdown_lines.append("")
        markdown_lines.append("Please provide:")
        markdown_lines.append("")
        markdown_lines.append("1. **Risk Assessment** - Any potential issues with automated fixes?")
        markdown_lines.append("2. **Step-by-Step Plan** - Exact commands to run in order")
        markdown_lines.append("3. **Verification Steps** - How to confirm fixes worked")
        markdown_lines.append("4. **Backup Strategy** - Should we create a backup first?")
        markdown_lines.append("")
        
        markdown_lines.append("### Suggested Workflow:")
        markdown_lines.append("")
        markdown_lines.append("```bash")
        markdown_lines.append("# 1. Create a backup branch")
        markdown_lines.append("git checkout -b fix/code-quality")
        markdown_lines.append("")
        markdown_lines.append("# 2. Fix critical errors manually (if any)")
        markdown_lines.append("# [Edit files as needed]")
        markdown_lines.append("")
        markdown_lines.append("# 3. Apply formatting fixes")
        markdown_lines.append(f"cd {repo_info.path} && black .")
        markdown_lines.append(f"cd {repo_info.path} && isort .")
        markdown_lines.append("")
        markdown_lines.append("# 4. Review and commit")
        markdown_lines.append("git diff --stat")
        markdown_lines.append("git add .")
        markdown_lines.append("git commit -m 'fix: apply code formatting and linting fixes'")
        markdown_lines.append("```")
        markdown_lines.append("")
        
        markdown_lines.append("### Next Steps for LLM:")
        markdown_lines.append("")
        markdown_lines.append("- [ ] Confirm the workflow above is safe")
        markdown_lines.append("- [ ] Identify any files that need manual review")
        markdown_lines.append("- [ ] Suggest testing procedures")
        markdown_lines.append("- [ ] Recommend prevention strategies (e.g., pre-commit hooks)")
        markdown_lines.append("")
        
        # Footer
        markdown_lines.append("---")
        markdown_lines.append("")
        markdown_lines.append("*This LLM-optimized report was generated by Weekly tool*")
        markdown_lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        markdown_lines.append("")
        markdown_lines.append("**End of Report**")
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(markdown_lines))
    
    @staticmethod
    def generate_markdown_report(
        results: Dict[str, CheckResult],
        repo_info: RepoInfo,
        output_path: Union[str, Path],
        title: str = "Weekly Git Report"
    ) -> None:
        """Generate a Markdown report for a repository scan.
        
        Args:
            results: Dictionary of check results
            repo_info: Repository information
            output_path: Path to save the Markdown report
            title: Report title
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate Markdown content
        markdown_lines = []
        
        # Header
        markdown_lines.append(f"# {title}")
        markdown_lines.append("")
        markdown_lines.append(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        markdown_lines.append("")
        
        # Repository info
        markdown_lines.append("## Repository Information")
        markdown_lines.append("")
        markdown_lines.append(f"- **Name:** {repo_info.org}/{repo_info.name}")
        markdown_lines.append(f"- **Branch:** {repo_info.branch}")
        markdown_lines.append(f"- **Path:** {repo_info.path}")
        markdown_lines.append(f"- **Status:** {'✅ All checks passed' if not any(not result.is_ok for result in results.values()) else '❌ Issues found'}")
        markdown_lines.append("")
        
        # Check results
        markdown_lines.append("## Check Results")
        markdown_lines.append("")
        
        for name, result in results.items():
            status_icon = "✅" if result.is_ok else "❌"
            markdown_lines.append(f"### {status_icon} {name.title()}")
            markdown_lines.append("")
            markdown_lines.append(f"**Status:** {result.message}")
            markdown_lines.append("")
            
            # Add detailed issues if available
            if result.metadata and 'issues_data' in result.metadata:
                issues_data = result.metadata['issues_data']
                
                for tool, issues in issues_data.items():
                    markdown_lines.append(f"#### {tool.upper()} Issues ({len(issues)} total)")
                    markdown_lines.append("")
                    
                    for issue in issues:
                        markdown_lines.append(f"- **File:** `{issue['file']}:{issue['line']}`")
                        markdown_lines.append(f"  - **Code:** `{issue['code']}`")
                        markdown_lines.append(f"  - **Message:** {issue['message']}")
                        markdown_lines.append(f"  - **Fix:** Run `{tool.lower()}` to fix this issue")
                        markdown_lines.append("")
            
            # Add next steps if available
            if result.next_steps:
                markdown_lines.append("**Next Steps:**")
                markdown_lines.append("")
                for step in result.next_steps:
                    markdown_lines.append(f"- {step}")
                markdown_lines.append("")
            
            markdown_lines.append("---")
            markdown_lines.append("")
        
        # Footer
        markdown_lines.append("---")
        markdown_lines.append(f"*Report generated by Weekly - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(markdown_lines))
    
    @staticmethod
    def generate_html_report(
        results: Dict[str, CheckResult],
        repo_info: RepoInfo,
        output_path: Union[str, Path],
        title: str = "Weekly Git Report"
    ) -> None:
        """Generate an HTML report for a repository scan.
        
        Args:
            results: Dictionary of check results
            repo_info: Repository information
            output_path: Path to save the HTML report
            title: Report title
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare the context
        context = {
            "title": title,
            "repo_info": asdict(repo_info),
            "results": [{
                "name": name,
                "description": result.description,
                "is_ok": result.is_ok,
                "message": result.message,
                "details": result.metadata if result.metadata else result.details,
                "next_steps": result.next_steps,
                "severity": result.severity
            } for name, result in results.items()],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "has_errors": any(not result.is_ok for result in results.values())
        }
        
        # Generate both Markdown and LLM-optimized reports
        md_output_path = output_path.with_suffix('.md')
        GitReportGenerator.generate_markdown_report(results, repo_info, md_output_path, title)
        
        llm_output_path = output_path.with_suffix('.llm.md')
        GitReportGenerator.generate_llm_report(results, repo_info, llm_output_path, title)
        
        # Generate the HTML
        html = GitReportGenerator._render_html_template("repo_report.html", context)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    @staticmethod
    def generate_summary_report(
        repos: List[Dict[str, Any]],
        output_path: Union[str, Path],
        title: str = "Weekly Scan Summary",
        scan_date: Optional[str] = None,
        since_date: Optional[str] = None
    ) -> None:
        """Generate a summary HTML report for multiple repositories.
        
        Args:
            repos: List of repository information dictionaries
            output_path: Path to save the HTML report
            title: Report title
            scan_date: Date of the scan (default: current date)
            since_date: Only include changes since this date
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare the context
        context = {
            "title": title,
            "repos": repos,
            "scan_date": scan_date or datetime.now().strftime("%Y-%m-%d"),
            "since_date": since_date,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Generate the HTML
        html = GitReportGenerator._render_html_template("summary_report.html", context)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    @staticmethod
    def _render_html_template(template_name: str, context: Dict[str, Any]) -> str:
        """Render an HTML template with the given context.
        
        Args:
            template_name: Name of the template file
            context: Dictionary of template variables
            
        Returns:
            Rendered HTML as a string
        """
        # This is a simplified version - in a real implementation, you would use a templating engine
        # like Jinja2 with proper template files
        
        if template_name == "repo_report.html":
            return GitReportGenerator._render_repo_report(context)
        elif template_name == "summary_report.html":
            return GitReportGenerator._render_summary_report(context)
        else:
            raise ValueError(f"Unknown template: {template_name}")
    
    @staticmethod
    def _render_repo_report(context: Dict[str, Any]) -> str:
        """Render the repository report template."""
        repo_info = context["repo_info"]
        results = context["results"]
        
        # Status badge
        status_badge = """
        <div class="status-badge">
            <span class="badge {badge_class}">{status_text}</span>
        </div>
        """.format(
            badge_class="badge-success" if not context["has_errors"] else "badge-error",
            status_text="All checks passed" if not context["has_errors"] else "Issues found"
        )
        
        # Results table
        results_table = ""
        for result in results:
            status_icon = "✓" if result["is_ok"] else "✗"
            status_class = "success" if result["is_ok"] else "error"
            
            # Format details with better structure
            details = ""
            if result["details"]:
                # Check if details is a dictionary with issues_data
                if isinstance(result["details"], dict) and 'issues_data' in result["details"]:
                    # This is from style checker with full issue data
                    issues_data = result["details"]['issues_data']
                    details_html = "<div class='issue-list'>"
                    
                    for tool, issues in issues_data.items():
                        details_html += f"<div class='tool-section'>"
                        details_html += f"<div class='tool-header'>{tool.upper()} - {len(issues)} issues</div>"
                        
                        for issue in issues[:100]:  # Limit to first 100 issues per tool for performance
                            details_html += f"""
                            <div class='issue-item'>
                                <div class='issue-file'>{issue['file']}:{issue['line']}</div>
                                <div><span class='issue-code'>{issue['code']}</span> - {issue['message']}</div>
                                <div style='margin-top: 5px; font-size: 0.9em; color: #666;'>
                                    Fix: Run <code>{tool.lower()}</code> to address this issue
                                </div>
                            </div>
                            """
                        
                        if len(issues) > 100:
                            details_html += f"<div style='text-align: center; padding: 10px; color: #666;'>... and {len(issues) - 100} more issues</div>"
                        
                        details_html += "</div>"
                    
                    details_html += "</div>"
                    details = details_html
                else:
                    # Fallback to pre-formatted text
                    details = f"<pre>{result['details']}</pre>"
            
            next_steps = ""
            if result["next_steps"]:
                next_steps = "<ul>" + "".join(f"<li>{step}</li>" for step in result["next_steps"]) + "</ul>"
            
            results_table += f"""
            <tr class="{status_class}">
                <td>{result['name']}</td>
                <td><span class="status-icon">{status_icon}</span> {result['message']}</td>
                <td>{details}</td>
                <td>{next_steps}</td>
            </tr>
            """
        
        # Full HTML
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{context['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ margin-bottom: 30px; }}
                .repo-info {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .status-badge {{ margin: 10px 0; }}
                .badge {{ 
                    display: inline-block; 
                    padding: 5px 10px; 
                    border-radius: 3px; 
                    color: white; 
                    font-weight: bold; 
                }}
                .badge-success {{ background: #28a745; }}
                .badge-error {{ background: #dc3545; }}
                table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin: 20px 0;
                }}
                th, td {{ 
                    padding: 12px; 
                    text-align: left; 
                    border-bottom: 1px solid #ddd;
                }}
                th {{ background: #f5f5f5; }}
                tr.success {{ background: #f0fff0; }}
                tr.error {{ background: #fff0f0; }}
                .status-icon {{ font-weight: bold; }}
                pre {{ 
                    background: #f8f9fa; 
                    padding: 10px; 
                    border-radius: 3px; 
                    overflow-x: auto;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                .issue-list {{
                    max-height: 500px;
                    overflow-y: auto;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    padding: 10px;
                    background: #f9f9f9;
                }}
                .issue-item {{
                    margin-bottom: 10px;
                    padding: 8px;
                    background: white;
                    border-radius: 3px;
                    border-left: 3px solid #dc3545;
                }}
                .issue-file {{
                    font-family: monospace;
                    font-weight: bold;
                    color: #0066cc;
                }}
                .issue-code {{
                    font-family: monospace;
                    background: #e9ecef;
                    padding: 2px 4px;
                    border-radius: 2px;
                    font-size: 0.9em;
                }}
                .tool-section {{
                    margin-bottom: 20px;
                }}
                .tool-header {{
                    background: #f5f5f5;
                    padding: 8px;
                    font-weight: bold;
                    border-radius: 3px;
                    margin-bottom: 10px;
                }}
                .footer {{ 
                    margin-top: 30px; 
                    text-align: center; 
                    color: #6c757d; 
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{context['title']}</h1>
                    <p>Generated on {context['timestamp']}</p>
                </div>
                
                <div class="repo-info">
                    <h2>{repo_info['org']}/{repo_info['name']}</h2>
                    <p>Branch: {repo_info['branch']}</p>
                    <p>Path: {repo_info['path']}</p>
                    {status_badge}
                </div>
                
                <h2>Check Results</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Check</th>
                            <th>Status</th>
                            <th>Details</th>
                            <th>Next Steps</th>
                        </tr>
                    </thead>
                    <tbody>
                        {results_table}
                    </tbody>
                </table>
                
                <div class="footer">
                    <p>Report generated by Weekly - {context['timestamp']}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def _render_summary_report(context: Dict[str, Any]) -> str:
        """Render the summary report template."""
        repos = context["repos"]
        
        # Repo cards
        repo_cards = ""
        for repo in repos:
            status_icon = "✓" if not repo.get("has_errors", False) else "✗"
            status_class = "success" if not repo.get("has_errors", False) else "error"
            
            repo_cards += f"""
            <div class="repo-card">
                <h3>{repo['name']} <span class="status-icon {status_class}">{status_icon}</span></h3>
                <p>Branch: {repo.get('branch', 'main')}</p>
                <p>Last commit: {repo.get('last_commit', 'N/A')}</p>
                <p><a href="{repo.get('report_path', '#')}">View full report →</a></p>
            </div>
            """
        
        # Full HTML
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{context['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ margin-bottom: 30px; }}
                .summary-info {{ 
                    background: #f5f5f5; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin-bottom: 20px;
                    display: flex;
                    justify-content: space-between;
                }}
                .repo-grid {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); 
                    gap: 20px; 
                    margin: 20px 0;
                }}
                .repo-card {{ 
                    background: white; 
                    border: 1px solid #ddd; 
                    border-radius: 5px; 
                    padding: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .repo-card h3 {{ margin-top: 0; }}
                .status-icon {{ 
                    font-weight: bold; 
                    margin-left: 5px;
                }}
                .status-icon.success {{ color: #28a745; }}
                .status-icon.error {{ color: #dc3545; }}
                .footer {{ 
                    margin-top: 30px; 
                    text-align: center; 
                    color: #6c757d; 
                    font-size: 0.9em;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{context['title']}</h1>
                    <p>Generated on {context['timestamp']}</p>
                </div>
                
                <div class="summary-info">
                    <div>
                        <h2>Scan Summary</h2>
                        <p>Repositories scanned: {len(repos)}</p>
                        {f"<p>Changes since: {context.get('since_date', 'N/A')}</p>" if context.get('since_date') else ''}
                    </div>
                </div>
                
                <h2>Repositories</h2>
                <div class="repo-grid">
                    {repo_cards}
                </div>
                
                <div class="footer">
                    <p>Report generated by Weekly - {context['timestamp']}</p>
                </div>
            </div>
        </body>
        </html>
        """
