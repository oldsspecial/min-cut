#!/usr/bin/env python
"""
Simple example demonstrating the Neo4j Min-Cut algorithm.

This script creates a small example graph and finds the minimum cut between two nodes.
It is designed to be a quick demonstration of the min-cut implementation.
"""

from mincut import MinCutFinder
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_example():
    """Create a simple graph and find the min-cut between two nodes."""
    # Connection parameters
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = ""
    
    finder = MinCutFinder(uri, user, password)
    
    try:
        # Connect to Neo4j
        finder.connect()
        
        # Create a simple example graph
        with finder.driver.session() as session:
            # Clean up any existing example data
            session.run("MATCH (n:ExampleNode) DETACH DELETE n")
            
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
            
            query = """
            CREATE 
              (a:ExampleNode {name: 'A'}),
              (b:ExampleNode {name: 'B'}),
              (c:ExampleNode {name: 'C'}),
              (d:ExampleNode {name: 'D'}),
              (e:ExampleNode {name: 'E'}),
              (f:ExampleNode {name: 'F'}),
              (a)-[:EXAMPLE_REL]->(b),
              (a)-[:EXAMPLE_REL]->(c),
              (b)-[:EXAMPLE_REL]->(d),
              (c)-[:EXAMPLE_REL]->(e),
              (d)-[:EXAMPLE_REL]->(f),
              (e)-[:EXAMPLE_REL]->(f),
              (b)-[:EXAMPLE_REL]->(e),
              (c)-[:EXAMPLE_REL]->(d)
            RETURN a, f
            """
            
            session.run(query)
            print("Created example graph with 6 nodes and 8 relationships")
            
            # Get node IDs for source and target
            query = """
            MATCH (source:ExampleNode {name: 'A'})
            MATCH (target:ExampleNode {name: 'F'})
            RETURN id(source) as source_id, id(target) as target_id
            """
            
            result = session.run(query)
            record = result.single()
            
            source_id = record["source_id"]
            target_id = record["target_id"]
        
        # Find the min-cut
        print("\nFinding minimum cut between nodes A and F...")
        min_cut = finder.find_min_cut(
            source_id,
            target_id,
            ["EXAMPLE_REL"],
            ["ExampleNode"],
            max_path_length=5
        )
        
        # Display the results
        print(f"\nFound {len(min_cut)} relationships in the min-cut:")
        
        with finder.driver.session() as session:
            for i, rel in enumerate(min_cut):
                rel_id = rel["id"]
                query = """
                MATCH (a)-[r]->(b) WHERE elementId(r) = $rel_id
                RETURN a.name as source, b.name as target
                """
                
                result = session.run(query, rel_id=rel_id)
                record = result.single()
                
                print(f"  {i+1}. {record['source']} -> {record['target']}")
        
        print("\nThe min-cut effectively separates the graph into two components:")
        print("  Component 1: Contains node A (the start node)")
        print("  Component 2: Contains node F (the end node)")
        print("\nRemoving these relationships would disconnect A from F with the minimum number of cuts.")
        
        # Clean up
        with finder.driver.session() as session:
            session.run("MATCH (n:ExampleNode) DETACH DELETE n")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nMake sure Neo4j is running with APOC and GDS plugins installed.")
        print("You may need to adjust the connection parameters (uri, user, password).")
    finally:
        finder.close()


if __name__ == "__main__":
    print("===== Neo4j Min-Cut Example =====")
    run_example()
