#!/usr/bin/env python
"""
Command-line utility for Neo4j Min-Cut algorithm.

This script provides a command-line interface to the Neo4j Min-Cut algorithm,
allowing users to find the minimum cut between two nodes in a Neo4j graph.
"""

import argparse
import json
import logging
import sys
from typing import List, Dict, Any, Optional, Union

from mincut import find_min_cut

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Find the minimum cut between two nodes in a Neo4j graph.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Required arguments
    parser.add_argument(
        "--start-node", 
        type=int, 
        required=True, 
        help="ID of the start node"
    )
    parser.add_argument(
        "--end-node", 
        type=int, 
        required=True, 
        help="ID of the end node"
    )
    parser.add_argument(
        "--node-labels", 
        type=str, 
        required=True, 
        help="Node labels to consider (comma-separated)"
    )
    parser.add_argument(
        "--relationship-types", 
        type=str, 
        required=True, 
        help="Relationship types to traverse (comma-separated)"
    )

    # Neo4j connection arguments
    parser.add_argument(
        "--uri", 
        type=str, 
        default="bolt://localhost:7687", 
        help="Neo4j connection URI"
    )
    parser.add_argument(
        "--username", 
        type=str, 
        default="neo4j", 
        help="Neo4j username"
    )
    parser.add_argument(
        "--password", 
        type=str, 
        default="password", 
        help="Neo4j password"
    )

    # Additional arguments
    parser.add_argument(
        "--max-path-length", 
        type=int, 
        default=10, 
        help="Maximum path length to consider"
    )
    parser.add_argument(
        "--output-format", 
        type=str, 
        choices=["json", "table", "text"], 
        default="text", 
        help="Output format"
    )
    parser.add_argument(
        "--output-file", 
        type=str, 
        help="Save output to file (in addition to stdout)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )

    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    """
    Configure logging level based on verbosity.
    
    Args:
        verbose (bool): Whether to enable verbose logging
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    else:
        logger.setLevel(logging.INFO)


def parse_list_arg(arg_value: str) -> List[str]:
    """
    Parse a comma-separated string into a list of strings.
    
    Args:
        arg_value (str): Comma-separated string
        
    Returns:
        List[str]: List of strings
    """
    return [item.strip() for item in arg_value.split(",")]


def format_output(min_cut: List[Dict[str, Any]], output_format: str) -> str:
    """
    Format the min-cut results according to the specified output format.
    
    Args:
        min_cut (List[Dict[str, Any]]): List of min-cut relationships
        output_format (str): Output format (json, table, text)
        
    Returns:
        str: Formatted output
    """
    if not min_cut:
        return "No min-cut found. The nodes might be disconnected or in the same component."

    if output_format == "json":
        return json.dumps(min_cut, indent=2)
    
    elif output_format == "table":
        if not min_cut:
            return "No min-cut relationships found."
        
        # Create a table-like output
        header = "| ID | Source | Target | Type |"
        separator = "|----|--------|--------|------|"
        rows = []
        
        for rel in min_cut:
            row = f"| {rel['id']} | {rel['source']} | {rel['target']} | {rel['type']} |"
            rows.append(row)
        
        return "\n".join([header, separator] + rows)
    
    else:  # text format
        if not min_cut:
            return "No min-cut relationships found."
        
        lines = [f"Found {len(min_cut)} relationships in the min-cut:"]
        
        for i, rel in enumerate(min_cut):
            lines.append(f"  {i+1}. ID: {rel['id']}, From: {rel['source']}, To: {rel['target']}, Type: {rel['type']}")
        
        return "\n".join(lines)


def save_to_file(content: str, filepath: str) -> None:
    """
    Save content to a file.
    
    Args:
        content (str): Content to save
        filepath (str): Path to the output file
    """
    try:
        with open(filepath, "w") as f:
            f.write(content)
        logger.info(f"Results saved to {filepath}")
    except Exception as e:
        logger.error(f"Failed to save results to {filepath}: {str(e)}")


def main() -> int:
    """
    Main function to run the command-line utility.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    args = parse_args()
    setup_logging(args.verbose)
    
    try:
        # Parse list arguments
        node_labels = parse_list_arg(args.node_labels)
        relationship_types = parse_list_arg(args.relationship_types)
        
        logger.debug(f"Finding min-cut from node {args.start_node} to {args.end_node}")
        logger.debug(f"Node labels: {node_labels}")
        logger.debug(f"Relationship types: {relationship_types}")
        logger.debug(f"Max path length: {args.max_path_length}")
        logger.debug(f"Neo4j URI: {args.uri}")
        

        # Run the min-cut algorithm
        min_cut = find_min_cut(
            start_node_id=args.start_node,
            end_node_id=args.end_node,
            node_labels=node_labels,
            relationship_types=relationship_types,
            max_path_length=args.max_path_length,
            uri=args.uri,
            user=args.username,
            password=args.password,
            ids_are_node_ids=True
        )
        print(min_cut)
        print(f"Found {len(min_cut)} relationships in the min-cut")
        # Format and display the results
        # output = format_output(min_cut, args.output_format)
        # print(output)
        
        # # Save to file if requested
        # if args.output_file:
        #     save_to_file(output, args.output_file)
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.verbose:
            logger.exception("Detailed error information:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
