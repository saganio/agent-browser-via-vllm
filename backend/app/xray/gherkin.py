"""
Gherkin parser for BDD scenarios

Parses Gherkin (Given/When/Then) syntax and converts it to natural language
commands that can be executed by the agent-browser orchestrator.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class StepType(str, Enum):
    """Gherkin step types"""
    GIVEN = "given"
    WHEN = "when"
    THEN = "then"
    AND = "and"
    BUT = "but"
    BACKGROUND = "background"


@dataclass
class GherkinStep:
    """Represents a single Gherkin step"""
    type: StepType
    text: str
    line_number: int
    data_table: Optional[List[Dict[str, str]]] = None
    doc_string: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "text": self.text,
            "line_number": self.line_number,
            "data_table": self.data_table,
            "doc_string": self.doc_string,
        }


@dataclass
class GherkinScenario:
    """Represents a parsed Gherkin scenario"""
    name: Optional[str]
    description: Optional[str]
    tags: List[str]
    steps: List[GherkinStep]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "steps": [s.to_dict() for s in self.steps],
        }


class GherkinParser:
    """Parser for Gherkin/Cucumber syntax"""
    
    # Keywords that start steps
    STEP_KEYWORDS = {
        "given": StepType.GIVEN,
        "when": StepType.WHEN,
        "then": StepType.THEN,
        "and": StepType.AND,
        "but": StepType.BUT,
        # Common non-English keywords
        "étant donné": StepType.GIVEN,  # French
        "quand": StepType.WHEN,
        "alors": StepType.THEN,
        "et": StepType.AND,
        "mais": StepType.BUT,
    }
    
    # Patterns for common browser actions
    BROWSER_ACTION_PATTERNS = [
        # Navigation
        (r"I (?:am on|go to|navigate to|open|visit) (?:the )?(.+?)(?:\s+page)?$", 
         "Navigate to {0}"),
        (r"I (?:open|load) (?:the )?URL ['\"]?([^'\"]+)['\"]?",
         "Navigate to {0}"),
        
        # Clicking
        (r"I (?:click|press|tap|select) (?:on )?(?:the )?['\"]?(.+?)['\"]?(?:\s+button|\s+link|\s+element)?$",
         "Click on {0}"),
        (r"I (?:click|press) (?:the )?(.+?)(?:\s+button|\s+link)?$",
         "Click on {0}"),
        
        # Text input
        (r"I (?:enter|type|input|fill|fill in) ['\"]?(.+?)['\"]? (?:in|into) (?:the )?['\"]?(.+?)['\"]?(?:\s+field|\s+input)?$",
         "Enter \"{0}\" into the {1} field"),
        (r"I (?:enter|type|input) ['\"]?(.+?)['\"]?$",
         "Enter \"{0}\""),
        (r"I (?:fill|fill in) (?:the )?['\"]?(.+?)['\"]? (?:field|input)? with ['\"]?(.+?)['\"]?$",
         "Enter \"{1}\" into the {0} field"),
        
        # Form submission
        (r"I (?:submit|send) (?:the )?(?:form|data)?$",
         "Submit the form"),
        (r"I (?:submit|send) (?:the )?(.+?) form$",
         "Submit the {0} form"),
        
        # Visibility/presence
        (r"I (?:should )?see (?:the )?['\"]?(.+?)['\"]?$",
         "Verify that \"{0}\" is visible on the page"),
        (r"(?:the )?['\"]?(.+?)['\"]? (?:is|should be) (?:displayed|visible|shown)$",
         "Verify that \"{0}\" is visible on the page"),
        (r"(?:the )?page (?:should )?(?:contain|show|display)s? ['\"]?(.+?)['\"]?$",
         "Verify that the page contains \"{0}\""),
        
        # Not visible
        (r"I (?:should )?not see (?:the )?['\"]?(.+?)['\"]?$",
         "Verify that \"{0}\" is not visible on the page"),
        (r"(?:the )?['\"]?(.+?)['\"]? (?:is|should be) (?:not displayed|hidden|invisible)$",
         "Verify that \"{0}\" is not visible on the page"),
        
        # Waiting
        (r"I wait (?:for )?(\d+) seconds?$",
         "Wait for {0} seconds"),
        (r"I wait for (?:the )?['\"]?(.+?)['\"]? (?:to appear|to be visible)?$",
         "Wait for \"{0}\" to appear"),
        
        # Screenshots
        (r"I (?:take|capture) (?:a )?screenshot$",
         "Take a screenshot"),
        
        # URL checks
        (r"(?:the )?(?:current )?URL (?:should be|is) ['\"]?(.+?)['\"]?$",
         "Verify the URL is \"{0}\""),
        (r"I (?:should be|am) (?:on|at) (?:the )?['\"]?(.+?)['\"]?(?:\s+page)?$",
         "Verify the current page is \"{0}\""),
        
        # Text content
        (r"(?:the )?['\"]?(.+?)['\"]? (?:should contain|contains) ['\"]?(.+?)['\"]?$",
         "Verify that {0} contains \"{1}\""),
        (r"(?:the )?['\"]?(.+?)['\"]? (?:should have|has) (?:the )?(?:text|value) ['\"]?(.+?)['\"]?$",
         "Verify that {0} has text \"{1}\""),
        
        # Checkbox/Radio
        (r"I (?:check|select) (?:the )?['\"]?(.+?)['\"]? checkbox$",
         "Check the \"{0}\" checkbox"),
        (r"I (?:uncheck|deselect) (?:the )?['\"]?(.+?)['\"]? checkbox$",
         "Uncheck the \"{0}\" checkbox"),
        
        # Dropdown
        (r"I select ['\"]?(.+?)['\"]? from (?:the )?['\"]?(.+?)['\"]? (?:dropdown|select)?$",
         "Select \"{0}\" from the {1} dropdown"),
        
        # Scrolling
        (r"I scroll (?:down|up|to (?:the )?(?:bottom|top))$",
         "Scroll {0}"),
        (r"I scroll to (?:the )?['\"]?(.+?)['\"]?$",
         "Scroll to element \"{0}\""),
        
        # Hover
        (r"I (?:hover|move) (?:over|to) (?:the )?['\"]?(.+?)['\"]?$",
         "Hover over \"{0}\""),
        
        # Login/Credentials
        (r"I (?:log in|login|sign in) (?:with|as) (?:username )?['\"]?(.+?)['\"]? and (?:password )?['\"]?(.+?)['\"]?$",
         "Log in with username \"{0}\" and password \"{1}\""),
        (r"I (?:log in|login|sign in)$",
         "Complete the login process"),
        
        # Logout
        (r"I (?:log out|logout|sign out)$",
         "Log out"),
    ]
    
    def __init__(self):
        # Compile patterns for efficiency
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), template)
            for pattern, template in self.BROWSER_ACTION_PATTERNS
        ]
    
    def parse(self, scenario_text: str) -> GherkinScenario:
        """Parse a Gherkin scenario text into structured data"""
        lines = scenario_text.strip().split('\n')
        
        tags: List[str] = []
        name: Optional[str] = None
        description: Optional[str] = None
        steps: List[GherkinStep] = []
        
        current_step_type: Optional[StepType] = None
        current_step_text: Optional[str] = None
        current_line: int = 0
        in_doc_string = False
        doc_string_content: List[str] = []
        data_table: List[Dict[str, str]] = []
        table_headers: List[str] = []
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Handle tags
            if stripped.startswith('@'):
                tags.extend([t.strip() for t in stripped.split() if t.startswith('@')])
                continue
            
            # Handle scenario name
            if stripped.lower().startswith('scenario:') or stripped.lower().startswith('scenario outline:'):
                name = stripped.split(':', 1)[1].strip()
                continue
            
            # Handle doc strings (""" blocks)
            if stripped.startswith('"""'):
                if in_doc_string:
                    # End of doc string
                    if current_step_text and steps:
                        steps[-1].doc_string = '\n'.join(doc_string_content)
                    in_doc_string = False
                    doc_string_content = []
                else:
                    in_doc_string = True
                continue
            
            if in_doc_string:
                doc_string_content.append(line)
                continue
            
            # Handle data tables (| col1 | col2 |)
            if stripped.startswith('|') and stripped.endswith('|'):
                cells = [c.strip() for c in stripped[1:-1].split('|')]
                if not table_headers:
                    table_headers = cells
                else:
                    row = dict(zip(table_headers, cells))
                    data_table.append(row)
                continue
            elif table_headers and data_table:
                # End of table, attach to previous step
                if steps:
                    steps[-1].data_table = data_table.copy()
                table_headers = []
                data_table = []
            
            # Check for step keywords
            lower_stripped = stripped.lower()
            step_type = None
            step_text = None
            
            for keyword, stype in self.STEP_KEYWORDS.items():
                if lower_stripped.startswith(keyword + ' '):
                    step_type = stype
                    step_text = stripped[len(keyword):].strip()
                    break
            
            if step_type and step_text:
                # Resolve 'And' and 'But' to the previous step type
                if step_type in (StepType.AND, StepType.BUT) and current_step_type:
                    resolved_type = current_step_type
                else:
                    resolved_type = step_type
                    if step_type not in (StepType.AND, StepType.BUT):
                        current_step_type = step_type
                
                steps.append(GherkinStep(
                    type=resolved_type,
                    text=step_text,
                    line_number=line_num
                ))
        
        # Handle any remaining data table
        if table_headers and data_table and steps:
            steps[-1].data_table = data_table
        
        return GherkinScenario(
            name=name,
            description=description,
            tags=tags,
            steps=steps
        )
    
    def step_to_command(self, step: GherkinStep) -> str:
        """Convert a Gherkin step to a natural language command"""
        text = step.text
        
        # Try to match against known patterns
        for pattern, template in self.compiled_patterns:
            match = pattern.match(text)
            if match:
                groups = match.groups()
                try:
                    return template.format(*groups)
                except (IndexError, KeyError):
                    pass
        
        # If no pattern matches, return the step text as-is with context
        prefix = {
            StepType.GIVEN: "Set up:",
            StepType.WHEN: "Action:",
            StepType.THEN: "Verify:",
            StepType.AND: "",
            StepType.BUT: "",
        }.get(step.type, "")
        
        return f"{prefix} {text}".strip()
    
    def scenario_to_commands(self, scenario: GherkinScenario) -> List[str]:
        """Convert a full scenario to a list of commands"""
        commands = []
        
        for step in scenario.steps:
            command = self.step_to_command(step)
            
            # Add data table info if present
            if step.data_table:
                table_info = " with data: " + ", ".join(
                    f"{k}={v}" for row in step.data_table for k, v in row.items()
                )
                command += table_info
            
            # Add doc string if present
            if step.doc_string:
                command += f" using:\n{step.doc_string}"
            
            commands.append(command)
        
        return commands
    
    def scenario_to_prompt(self, scenario: GherkinScenario) -> str:
        """Convert a scenario to a single prompt for the LLM"""
        commands = self.scenario_to_commands(scenario)
        
        prompt_parts = []
        
        if scenario.name:
            prompt_parts.append(f"Test: {scenario.name}")
        
        if scenario.description:
            prompt_parts.append(f"Description: {scenario.description}")
        
        prompt_parts.append("\nSteps to execute:")
        for i, cmd in enumerate(commands, 1):
            prompt_parts.append(f"{i}. {cmd}")
        
        return "\n".join(prompt_parts)


def parse_gherkin(scenario_text: str) -> GherkinScenario:
    """Convenience function to parse Gherkin text"""
    parser = GherkinParser()
    return parser.parse(scenario_text)


def gherkin_to_prompt(scenario_text: str) -> str:
    """Convenience function to convert Gherkin to a prompt"""
    parser = GherkinParser()
    scenario = parser.parse(scenario_text)
    return parser.scenario_to_prompt(scenario)


def gherkin_to_commands(scenario_text: str) -> List[str]:
    """Convenience function to convert Gherkin to command list"""
    parser = GherkinParser()
    scenario = parser.parse(scenario_text)
    return parser.scenario_to_commands(scenario)
