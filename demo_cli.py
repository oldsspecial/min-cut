#!/usr/bin/env python
"""
Demo script to demonstrate the min_cut_cli.py command-line utility.

This script creates a simple example graph and shows how to use the min_cut_cli.py
command-line utility to find the minimum cut between two nodes.
"""

from neo4j import GraphDatabase
import subprocess
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Neo4j connection parameters
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "password"  # Change this to your Neo4j password

def create_example_graph():
    """
    Create a simple example graph for demonstrating the min-cut CLI.
    
    Returns:
        tuple: (source_id, target_id) - IDs of the source and target nodes
    """
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    
    try:
        with driver.session() as session:
            # Clean up any existing example data
            session.run("MATCH (n:CliDemo) DETACH DELETE n")
            
            # Create a simple graph with a clear min-cut
            # This creates a "butterfly" graph with a narrow waist
            #
            #      B --- D
            #     /       \
            #    A         F
            #     \       /
            #      C --- E
            #
            # The min-cut between A and F consists of the edges D-F and E-F
            
            logger.info("Creating example graph for min-cut CLI demo...")
            query = """
            CREATE 
              (a:CliDemo {name: 'A'}),
              (b:CliDemo {name: 'B'}),
              (c:CliDemo {name: 'C'}),
              (d:CliDemo {name: 'D'}),
              (e:CliDemo {name: 'E'}),
              (f:CliDemo {name: 'F'}),
              (a)-[:DEMO_REL]->(b),
              (a)-[:DEMO_REL]->(c),
              (b)-[:DEMO_REL]->(d),
              (c)-[:DEMO_REL]->(e),
              (d)-[:DEMO_REL]->(f),
              (e)-[:DEMO_REL]->(f),
              (b)-[:DEMO_REL]->(e),
              (c)-[:DEMO_REL]->(d)
            RETURN a, f
            """
            
            session.run(query)
            logger.info("Created example graph with 6 nodes and 8 relationships")
            
            # Get node IDs for source and target
            query = """
            MATCH (source:CliDemo {name: 'A'})
            MATCH (target:CliDemo {name: 'F'})
            RETURN elementId(source) as source_id, elementId(target) as target_id
            """
            
            result = session.run(query)
            record = result.single()
            
            if not record:
                logger.error("Failed to get node IDs")
                return None, None
            
            source_id = record["source_id"]
            target_id = record["target_id"]
            
            logger.info(f"Source node (A) ID: {source_id}")
            logger.info(f"Target node (F) ID: {target_id}")
            
            return source_id, target_id
            
    except Exception as e:
        logger.error(f"Error creating example graph: {str(e)}")
        return None, None
    finally:
        driver.close()

def demonstrate_cli(source_id, target_id):
    """
    Demonstrate the min_cut_cli.py command-line utility.
    
    Args:
        source_id: ID of the source node
        target_id: ID of the target node
    """
    if source_id is None or target_id is None:
        logger.error("Cannot demonstrate CLI without valid node IDs")
        return
    
    logger.info("\n=== Running min_cut_cli.py with text output (default) ===")
    text_cmd = [
        "python", "min_cut_cli.py",
        "--start-node", str(source_id),
        "--end-node", str(target_id),
        "--node-labels", "CliDemo",
        "--relationship-types", "DEMO_REL",
        "--username", USERNAME,
        "--password", PASSWORD
    ]
    subprocess.run(text_cmd)
    
    logger.info("\n=== Running min_cut_cli.py with table output ===")
    table_cmd = [
        "python", "min_cut_cli.py",
        "--start-node", str(source_id),
        "--end-node", str(target_id),
        "--node-labels", "CliDemo",
        "--relationship-types", "DEMO_REL",
        "--output-format", "table",
        "--username", USERNAME,
        "--password", PASSWORD
    ]
    subprocess.run(table_cmd)
    
    logger.info("\n=== Running min_cut_cli.py with JSON output ===")
    json_cmd = [
        "python", "min_cut_cli.py",
        "--start-node", str(source_id),
        "--end-node", str(target_id),
        "--node-labels", "CliDemo",
        "--relationship-types", "DEMO_REL",
        "--output-format", "json",
        "--username", USERNAME,
        "--password", PASSWORD
    ]
    subprocess.run(json_cmd)

def cleanup():
    """
    Clean up the example graph.
    """
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    
    try:
        with driver.session() as session:
            session.run("MATCH (n:CliDemo) DETACH DELETE n")
            logger.info("Cleaned up example graph")
    except Exception as e:
        logger.error(f"Error cleaning up: {str(e)}")
    finally:
        driver.close()

def main():
    """
    Main function to run the demo.
    """
    logger.info("Starting Min-Cut CLI Demo")
    
    try:
        # Create the example graph and get node IDs
        source_id, target_id = create_example_graph()
        
        if source_id is not None and target_id is not None:
            # Demonstrate the CLI
            demonstrate_cli(source_id, target_id)
    except Exception as e:
        logger.error(f"Error in demo: {str(e)}")
    finally:
        # Clean up
        cleanup()
        logger.info("Demo completed")

if __name__ == "__main__":
    main()
