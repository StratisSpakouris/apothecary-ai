#!/usr/bin/env python3
"""
Apothecary-AI Interactive CLI

Command-line interface for interacting with Apothecary-AI via A2A protocol.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
from src.orchestrator import ApothecaryOrchestrator
from src.agui_protocol import (
    StatusUpdate,
    ResultMessage,
    SuggestionsMessage,
    FinalResponse,
    AgentStatus
)
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init(autoreset=True)


def print_header():
    """Print CLI header"""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}🧪 APOTHECARY-AI - AI-Powered Pharmacy Inventory Management")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")


def print_help():
    """Print available commands and examples"""
    print(f"{Fore.YELLOW}Available Commands:{Style.RESET_ALL}")
    print("  /help     - Show this help message")
    print("  /examples - Show example prompts")
    print("  /quit     - Exit the CLI")
    print("\n" + f"{Fore.GREEN}Example Prompts:{Style.RESET_ALL}")
    print("  - Show me the prescription history for patient P001")
    print("  - What's the current inventory of Lisinopril?")
    print("  - Analyze patient refill patterns")
    print("  - Forecast demand for cardiovascular medications for next 30 days")
    print("  - Run complete inventory analysis and recommend orders")
    print()


def print_examples():
    """Print detailed example prompts"""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}EXAMPLE PROMPTS BY USE CASE")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")

    examples = [
        {
            "category": "📊 Simple Data Queries (Fast - No Agent)",
            "prompts": [
                "Show me the prescription history for patient P001",
                "What's the current inventory of Metformin?",
                "List all medication categories",
                "Tell me about Lisinopril",
                "What cardiovascular medications do we have in stock?"
            ]
        },
        {
            "category": "👥 Patient Analysis",
            "prompts": [
                "Analyze patient refill patterns",
                "Which patients need refills this week?",
                "Identify high-risk patients",
                "Show me patient behavior breakdown"
            ]
        },
        {
            "category": "📈 Demand Forecasting",
            "prompts": [
                "Forecast demand for the next 30 days",
                "What's the summer demand forecast for antihistamines?",
                "Predict cardiovascular medication demand for next month",
                "How will flu season affect antiviral demand?"
            ]
        },
        {
            "category": "🎯 Complete Analysis & Orders",
            "prompts": [
                "Run complete inventory analysis",
                "What medications should I order?",
                "Generate optimal order recommendations",
                "Show me critical orders that need immediate attention"
            ]
        }
    ]

    for ex in examples:
        print(f"{Fore.YELLOW}{ex['category']}{Style.RESET_ALL}")
        for prompt in ex['prompts']:
            print(f"  • {prompt}")
        print()


def render_agui_message(message):
    """Render an AG-UI message with appropriate formatting"""
    if isinstance(message, StatusUpdate):
        # Status update
        status_icon = {
            AgentStatus.STARTING: "🔄",
            AgentStatus.WORKING: "⚙️ ",
            AgentStatus.COMPLETED: "✅",
            AgentStatus.FAILED: "❌"
        }.get(message.status, "•")

        print(f"{Fore.BLUE}{status_icon} [{message.agent}]{Style.RESET_ALL} {message.message}")

    elif isinstance(message, ResultMessage):
        # Result message
        print(f"\n{Fore.GREEN}✓ {message.agent} completed:{Style.RESET_ALL}")
        print(f"  {message.summary}")
        if message.reasoning:
            print(f"  {Fore.CYAN}→{Style.RESET_ALL} {message.reasoning}")

    elif isinstance(message, SuggestionsMessage):
        # Suggestions
        print(f"\n{Fore.YELLOW}📋 Suggested Next Actions:{Style.RESET_ALL}")
        for i, action in enumerate(message.actions, 1):
            print(f"  {Fore.YELLOW}[{i}]{Style.RESET_ALL} {action.label}")
            print(f"      {Fore.CYAN}{action.description}{Style.RESET_ALL}")

    elif isinstance(message, FinalResponse):
        # Final response
        print(f"\n{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✓ {message.summary}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Execution time: {message.execution_time_seconds:.2f}s{Style.RESET_ALL}")


def render_agui_response(response):
    """Render a complete AG-UI response"""
    if isinstance(response, FinalResponse):
        # Render all collected messages
        for result in response.results:
            render_agui_message(result)

        # Render final summary
        print(f"\n{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✓ {response.summary}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*80}{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}Execution time: {response.execution_time_seconds:.2f}s{Style.RESET_ALL}")

        # Render suggestions if available
        if response.suggestions:
            print(f"\n{Fore.YELLOW}📋 Suggested Next Actions:{Style.RESET_ALL}")
            for i, action in enumerate(response.suggestions.actions, 1):
                print(f"  {Fore.YELLOW}[{i}]{Style.RESET_ALL} {action.label}")
                print(f"      {Fore.CYAN}{action.description}{Style.RESET_ALL}")

            return response.suggestions  # Return for interactive selection

    else:
        # Non-AG-UI response (fallback)
        print(response)

    return None


def handle_suggestion_selection(orchestrator: ApothecaryOrchestrator, suggestions: SuggestionsMessage):
    """Handle user selection of a suggested action"""
    if not suggestions or not suggestions.actions:
        return None

    print(f"\n{Fore.YELLOW}Select an action (1-{len(suggestions.actions)}) or press Enter to skip:{Style.RESET_ALL}")

    try:
        selection = input(f"{Fore.CYAN}>>> {Style.RESET_ALL}").strip()

        if not selection:
            return None

        try:
            index = int(selection) - 1
            if 0 <= index < len(suggestions.actions):
                selected_action = suggestions.actions[index]
                print(f"\n{Fore.GREEN}Executing: {selected_action.label}{Style.RESET_ALL}\n")

                # Route the selected action
                if orchestrator.action_router:
                    import asyncio
                    result = asyncio.run(orchestrator.action_router.route_action(selected_action))
                    return result
                else:
                    print(f"{Fore.RED}Action routing not available{Style.RESET_ALL}")
                    return None
            else:
                print(f"{Fore.RED}Invalid selection{Style.RESET_ALL}")
                return None

        except ValueError:
            print(f"{Fore.RED}Invalid input{Style.RESET_ALL}")
            return None

    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        return None


def interactive_mode(orchestrator: ApothecaryOrchestrator):
    """Run interactive CLI mode with AG-UI support"""
    print_header()
    print(f"{Fore.GREEN}Interactive Mode - Type your query or /help for assistance{Style.RESET_ALL}\n")

    # Register AG-UI callback for real-time updates
    if orchestrator.agui:
        orchestrator.agui.register_callback(render_agui_message)

    while True:
        try:
            # Get user input
            user_input = input(f"{Fore.CYAN}>>> {Style.RESET_ALL}").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ['/quit', '/exit', '/q']:
                print(f"\n{Fore.YELLOW}Goodbye! 👋{Style.RESET_ALL}\n")
                break

            elif user_input.lower() == '/help':
                print_help()
                continue

            elif user_input.lower() == '/examples':
                print_examples()
                continue

            # Process via orchestrator
            print()  # Blank line

            response = orchestrator.run(user_input)

            # Render AG-UI response
            suggestions = render_agui_response(response)

            # Handle suggested actions
            if suggestions:
                follow_up = handle_suggestion_selection(orchestrator, suggestions)
                if follow_up:
                    # Render follow-up response
                    render_agui_response(follow_up)

            print()  # Blank line

        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}Interrupted. Use /quit to exit{Style.RESET_ALL}\n")

        except Exception as e:
            print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}\n")


def single_query_mode(orchestrator: ApothecaryOrchestrator, query: str):
    """Run single query and exit with AG-UI support"""
    print_header()
    print(f"{Fore.CYAN}Query:{Style.RESET_ALL} {query}\n")

    # Register AG-UI callback for real-time updates
    if orchestrator.agui:
        orchestrator.agui.register_callback(render_agui_message)

    try:
        response = orchestrator.run(query)

        # Render AG-UI response
        suggestions = render_agui_response(response)

        # Show suggestions in single query mode but don't prompt
        if suggestions:
            print(f"\n{Fore.CYAN}(Interactive mode would allow selecting these actions){Style.RESET_ALL}")

        print()

    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}\n")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Apothecary-AI Interactive CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python scripts/apothecary_cli.py

  # Single query mode
  python scripts/apothecary_cli.py --query "Show me inventory for Metformin"

  # Show examples
  python scripts/apothecary_cli.py --examples
        """
    )

    parser.add_argument(
        '--query', '-q',
        type=str,
        help='Run a single query and exit'
    )

    parser.add_argument(
        '--examples', '-e',
        action='store_true',
        help='Show example prompts and exit'
    )

    args = parser.parse_args()

    # Show examples and exit
    if args.examples:
        print_examples()
        return

    # Check data files exist
    data_files = [
        Path("data/raw/patients/prescription_history.csv"),
        Path("data/raw/inventory/current_stock.csv"),
        Path("data/raw/medications/medication_database.csv")
    ]

    missing_files = [f for f in data_files if not f.exists()]
    if missing_files:
        print(f"{Fore.RED}Error: Missing data files:{Style.RESET_ALL}")
        for f in missing_files:
            print(f"  - {f}")
        print(f"\n{Fore.YELLOW}Please ensure data files are in place before running.{Style.RESET_ALL}")
        sys.exit(1)

    # Initialize orchestrator
    print(f"{Fore.YELLOW}Initializing Apothecary-AI Orchestrator...{Style.RESET_ALL}")

    try:
        orchestrator = ApothecaryOrchestrator()
        print(f"{Fore.GREEN}✓ Orchestrator ready{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}Failed to initialize orchestrator: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

    # Run mode based on arguments
    if args.query:
        single_query_mode(orchestrator, args.query)
    else:
        interactive_mode(orchestrator)


if __name__ == "__main__":
    main()
