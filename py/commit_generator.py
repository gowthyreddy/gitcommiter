#!/usr/bin/env python3

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, TypedDict
from dataclasses import dataclass

import git
import google.generativeai as genai
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console()

@dataclass
class Config:
    api_key: str
    model: str = "gemini-1.5-flash"
    temperature: float = 0.3
    max_tokens: int = 100

class GraphState(TypedDict):
    messages: List[BaseMessage]
    git_diff: str
    staged_files: List[str]
    commit_message: str
    analysis_result: str
    change_type: str
    scope: str

class CommitMessageGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.llm = ChatGoogleGenerativeAI(
            model=config.model,
            google_api_key=config.api_key,
            temperature=config.temperature,
            max_output_tokens=config.max_tokens
        )
        
    def get_git_info(self, repo_path: str) -> tuple[str, List[str]]:
        """Get git diff and staged files."""
        try:
            repo = git.Repo(repo_path)
            
            # Get staged files
            staged_files = [item.a_path for item in repo.index.diff("HEAD")]
            
            # If no staged files, get modified files
            if not staged_files:
                modified_files = [item.a_path for item in repo.index.diff(None)]
                if modified_files:
                    # Auto-stage modified files
                    repo.git.add('.')
                    staged_files = [item.a_path for item in repo.index.diff("HEAD")]
            
            # Get the diff
            if staged_files:
                diff = repo.git.diff('--staged')
            else:
                diff = repo.git.diff()
                
            return diff, staged_files
            
        except git.exc.InvalidGitRepositoryError:
            raise ValueError("Not a git repository")
        except Exception as e:
            logger.error(f"Git error: {e}")
            raise
    
    def create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(GraphState)
        
        # Add nodes
        workflow.add_node("analyze_diff", self.analyze_diff)
        workflow.add_node("determine_type", self.determine_type)
        workflow.add_node("generate_message", self.generate_message)
        workflow.add_node("refine_message", self.refine_message)
        
        # Define the flow
        workflow.set_entry_point("analyze_diff")
        workflow.add_edge("analyze_diff", "determine_type")
        workflow.add_edge("determine_type", "generate_message")
        workflow.add_edge("generate_message", "refine_message")
        workflow.add_edge("refine_message", END)
        
        return workflow.compile()
    
    async def analyze_diff(self, state: GraphState) -> Dict:
        """Analyze the git diff to understand the changes."""
        analysis_prompt = f"""
Analyze the following git diff and provide a structured analysis:

Git Diff:
{state['git_diff'][:5000]}

Staged Files: {', '.join(state['staged_files'])}

Analyze the changes and provide:
1. What type of changes were made?
2. Which files/modules are most affected?
3. What is the main purpose of these changes?
4. Are there any breaking changes?
5. What would be an appropriate scope (component/module name)?

Be concise and focus on the most important aspects.
"""
        
        try:
            messages = [HumanMessage(content=analysis_prompt)]
            response = await self.llm.ainvoke(messages)
            analysis_result = response.content
            
            return {
                "analysis_result": analysis_result,
                "messages": state["messages"] + [HumanMessage(content=analysis_prompt), AIMessage(content=analysis_result)]
            }
        except Exception as e:
            logger.error(f"Error in analyze_diff: {e}")
            return {
                "analysis_result": f"Error analyzing changes: {str(e)}",
                "messages": state["messages"]
            }
    
    async def determine_type(self, state: GraphState) -> Dict:
        """Determine the commit type and scope."""
        type_prompt = f"""
Based on this analysis of git changes, determine the conventional commit type and scope:

Analysis:
{state['analysis_result']}

Files changed: {', '.join(state['staged_files'])}

Return ONLY a JSON object with this format:
{{
    "type": "one of: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert",
    "scope": "optional scope like component/module name or empty string"
}}

Guidelines for type selection:
- feat: New features or functionality
- fix: Bug fixes
- refactor: Code restructuring without changing behavior
- perf: Performance improvements
- style: Formatting, whitespace, missing semicolons
- docs: Documentation changes
- test: Adding or modifying tests
- chore: Maintenance tasks, dependency updates
- ci: CI/CD pipeline changes
- build: Build system or external dependencies
"""
        
        try:
            messages = [HumanMessage(content=type_prompt)]
            response = await self.llm.ainvoke(messages)
            
            # Try to parse JSON response
            try:
                result = json.loads(response.content.strip())
                change_type = result.get("type", "chore")
                scope = result.get("scope", "")
            except json.JSONDecodeError:
                # Fallback based on content analysis
                content = response.content.lower()
                if any(word in content for word in ["new", "add", "implement", "feature"]):
                    change_type = "feat"
                elif any(word in content for word in ["fix", "bug", "error", "issue"]):
                    change_type = "fix"
                elif any(word in content for word in ["refactor", "restructure", "reorganize"]):
                    change_type = "refactor"
                elif any(word in content for word in ["performance", "optimize", "speed"]):
                    change_type = "perf"
                elif any(word in content for word in ["style", "format", "whitespace"]):
                    change_type = "style"
                elif any(word in content for word in ["doc", "readme", "comment"]):
                    change_type = "docs"
                elif any(word in content for word in ["test", "spec"]):
                    change_type = "test"
                else:
                    change_type = "chore"
                scope = ""
            
            return {
                "change_type": change_type,
                "scope": scope,
                "messages": state["messages"] + [HumanMessage(content=type_prompt), AIMessage(content=response.content)]
            }
        except Exception as e:
            logger.error(f"Error in determine_type: {e}")
            return {
                "change_type": "chore",
                "scope": "",
                "messages": state["messages"]
            }
    
    async def generate_message(self, state: GraphState) -> Dict:
        """Generate the commit message."""
        scope_part = f"({state['scope']})" if state['scope'] else ""
        
        generate_prompt = f"""
Generate a conventional commit message description for these changes:

Type: {state['change_type']}
Scope: {state['scope']}
Analysis: {state['analysis_result']}
Files changed: {', '.join(state['staged_files'])}

Create a clear, specific description that explains what was changed and why.

Rules:
1. Use imperative mood ("add" not "added" or "adds")
2. Don't capitalize the first letter of description
3. Don't end with a period
4. Be specific about the actual functionality changed
5. Keep it under 95 characters total for the full message
6. Focus on the "what" and "why", not the "how"

Examples:
- adjust image resize dimensions for better accuracy
- fix null pointer exception in user validation
- add OAuth2 authentication support
- refactor database connection logic
- update API documentation for v2 endpoints
- optimize query performance in user search

Return ONLY the description part (what comes after the colon and space).
"""
        
        try:
            messages = [HumanMessage(content=generate_prompt)]
            response = await self.llm.ainvoke(messages)
            description = response.content.strip().strip('"\'')
            
            # Construct the full commit message
            commit_message = f"{state['change_type']}{scope_part}: {description}"
            
            return {
                "commit_message": commit_message,
                "messages": state["messages"] + [HumanMessage(content=generate_prompt), AIMessage(content=response.content)]
            }
        except Exception as e:
            logger.error(f"Error in generate_message: {e}")
            scope_part = f"({state['scope']})" if state['scope'] else ""
            return {
                "commit_message": f"{state['change_type']}{scope_part}: update files",
                "messages": state["messages"]
            }
    
    async def refine_message(self, state: GraphState) -> Dict:
        """Refine the commit message to ensure it follows conventions."""
        message = state['commit_message']
        
        # Remove quotes if present
        message = message.strip().strip('"\'')
        
        # Ensure it doesn't end with a period
        message = message.rstrip('.')
        
        # Ensure it's not too long (allow up to 95 chars for descriptive messages)
        if len(message) > 95:
            colon_index = message.find(': ')
            if colon_index > 0:
                prefix = message[:colon_index + 2]
                description = message[colon_index + 2:]
                max_desc_length = 95 - len(prefix) - 3  # -3 for "..."
                if len(description) > max_desc_length:
                    message = prefix + description[:max_desc_length] + '...'
            else:
                message = message[:92] + '...'
        
        # Intelligent fallback based on file analysis
        if len(message) < 10 or ': ' not in message:
            # Extract context from files and generate meaningful fallback
            file_names = [Path(f).stem.lower() for f in state['staged_files'][:3]]
            file_extensions = list(set(Path(f).suffix for f in state['staged_files'] if Path(f).suffix))
            
            # Try to infer purpose from file names and content
            context_keywords = ' '.join(file_names + [state['git_diff'][:500]]).lower()
            
            if any(word in context_keywords for word in ['test', 'spec', 'unittest']):
                message = "test: add test cases"
            elif any(word in context_keywords for word in ['readme', 'doc', 'documentation']):
                message = "docs: update documentation"
            elif any(word in context_keywords for word in ['config', 'setting', 'env']):
                message = "chore: update configuration"
            elif any(word in context_keywords for word in ['style', 'css', 'scss']):
                message = "style: update styling"
            elif any(word in context_keywords for word in ['fix', 'bug', 'error']):
                message = "fix: resolve issues"
            elif any(word in context_keywords for word in ['feature', 'new', 'add']):
                message = "feat: add new functionality"
            elif file_extensions:
                ext_list = ', '.join(file_extensions[:2])
                message = f"chore: update {ext_list} files"
            else:
                message = "chore: update project files"
        
        return {
            "commit_message": message,
            "messages": state["messages"]
        }
    
    async def generate(self, repo_path: str) -> Optional[str]:
        """Generate a commit message for the given repository."""
        try:
            # Get git information
            git_diff, staged_files = self.get_git_info(repo_path)
            
            if not git_diff.strip() and not staged_files:
                return None
            
            # Create initial state
            initial_state = GraphState(
                messages=[],
                git_diff=git_diff,
                staged_files=staged_files,
                commit_message="",
                analysis_result="",
                change_type="",
                scope=""
            )
            
            # Run the workflow
            workflow = self.create_workflow()
            final_state = await workflow.ainvoke(initial_state)
            
            return final_state.get("commit_message")
            
        except Exception as e:
            logger.error(f"Error generating commit message: {e}")
            raise

def main(
    repo_path: str = typer.Argument(default=".", help="Path to git repository"),
    api_key: str = typer.Option(None, "--api-key", help="Google AI API key"),
    model: str = typer.Option("gemini-1.5-flash", "--model", help="Model to use"),
    temperature: float = typer.Option(0.3, "--temperature", help="Generation temperature"),
    max_tokens: int = typer.Option(100, "--max-tokens", help="Maximum tokens"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Generate commit messages using AI and LangGraph."""
    
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        console.print("[red]Error: Google API key is required. Set GOOGLE_API_KEY environment variable or use --api-key[/red]")
        sys.exit(1)
    
    config = Config(
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    generator = CommitMessageGenerator(config)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating commit message...", total=None)
            
            import asyncio
            commit_message = asyncio.run(generator.generate(repo_path))
            
            progress.remove_task(task)
        
        if commit_message:
            if output_json:
                result = {"commit_message": commit_message, "success": True}
                print(json.dumps(result))
            else:
                console.print(f"[green]Generated commit message:[/green] {commit_message}")
        else:
            if output_json:
                result = {"commit_message": None, "success": False, "error": "No changes detected"}
                print(json.dumps(result))
            else:
                console.print("[yellow]No changes detected to generate commit message[/yellow]")
            sys.exit(1)
            
    except Exception as e:
        if output_json:
            result = {"commit_message": None, "success": False, "error": str(e)}
            print(json.dumps(result))
        else:
            console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    typer.run(main)