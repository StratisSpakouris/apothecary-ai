"""
ADK-Compatible Base Agent

Wraps Google Agent Development Kit (ADK) functionality for LLM-powered agents.
This provides a higher-level interface tailored to our use cases.
"""

import os
from typing import Any, Optional, List
from google.adk.agents import LlmAgent
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ADKAgent:
    """
    Base class for agents that leverage Google ADK and LLMs.

    This wraps ADK's LlmAgent to provide:
    - Standardized initialization with API key management
    - Consistent logging interface
    - Simplified tool integration
    - Error handling patterns

    Use this for agents that need:
    - Natural language understanding
    - Complex reasoning
    - Dynamic decision making
    - Text generation/analysis
    """

    def __init__(
        self,
        name: str,
        instruction: str,
        description: str,
        model: str = "gemini-2.0-flash-exp",
        tools: Optional[List[Any]] = None,
        sub_agents: Optional[List[Any]] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize ADK-powered agent.

        Args:
            name: Agent name (used for logging and ADK)
            instruction: System instruction/prompt for the agent's behavior
            description: Brief description of agent's purpose
            model: Gemini model to use (default: gemini-2.0-flash-exp)
            tools: List of ADK tools the agent can use
            sub_agents: List of sub-agents for hierarchical orchestration
            api_key: Google API key (if not provided, reads from GOOGLE_API_KEY env var)
        """
        self.name = name
        self.instruction = instruction
        self.description = description
        self.model = model
        self.logger = self._setup_logger()

        # Set up API key
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        elif "GOOGLE_API_KEY" not in os.environ:
            raise ValueError(
                "GOOGLE_API_KEY not found. Either:\n"
                "1. Set GOOGLE_API_KEY environment variable\n"
                "2. Create .env file with GOOGLE_API_KEY=your_key\n"
                "3. Pass api_key parameter to agent"
            )

        # Create ADK agent
        self.logger.info(f"Initializing ADK agent '{name}' with model {model}")
        try:
            self.agent = LlmAgent(
                name=name,
                model=model,
                instruction=instruction,
                description=description,
                tools=tools or [],
                sub_agents=sub_agents or []
            )
            self.logger.info("ADK agent initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize ADK agent: {e}")
            raise

    def _setup_logger(self) -> logging.Logger:
        """Setup agent-specific logger."""
        logger = logging.getLogger(self.name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.name} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def execute(self, prompt: str, **kwargs) -> Any:
        """
        Execute agent with a prompt.

        Args:
            prompt: The input prompt/query for the agent
            **kwargs: Additional parameters to pass to ADK agent

        Returns:
            Agent's response
        """
        self.logger.info(f"Executing with prompt length: {len(prompt)} chars")

        try:
            response = self.agent.run(prompt, **kwargs)
            self.logger.info("Execution completed successfully")
            return response
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            raise

    def run(self, prompt: str, **kwargs) -> Any:
        """
        Alias for execute() to match ADK's interface.

        Args:
            prompt: The input prompt/query for the agent
            **kwargs: Additional parameters to pass to ADK agent

        Returns:
            Agent's response
        """
        return self.execute(prompt, **kwargs)

    def add_tool(self, tool: Any) -> None:
        """
        Add a tool to the agent's toolkit.

        Args:
            tool: ADK Tool instance (BaseTool, FunctionTool, etc.)
        """
        self.agent.tools.append(tool)
        self.logger.info(f"Added tool: {tool.name if hasattr(tool, 'name') else 'unknown'}")

    def add_sub_agent(self, sub_agent: Any) -> None:
        """
        Add a sub-agent for hierarchical orchestration.

        Args:
            sub_agent: Another ADKAgent or LlmAgent instance
        """
        self.agent.sub_agents.append(sub_agent)
        sub_name = sub_agent.name if hasattr(sub_agent, 'name') else 'unknown'
        self.logger.info(f"Added sub-agent: {sub_name}")

    def __repr__(self):
        return f"<ADKAgent(name={self.name}, model={self.model})>"
