"""
Test cases for the Neo4j Min-Cut algorithm.

This module provides test cases for the min_cut module. It requires a running Neo4j 
instance with APOC and GDS plugins installed.
"""

import logging
import unittest
from mincut import find_min_cut, MinCutFinder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestMinCut(unittest.TestCase):
    """Test cases for the min_cut module."""
    
    def setUp(self):
        """Set up test database with a sample graph."""
        self.uri = "bolt://localhost:7687"
        self.user = "neo4j"
        self.password = "password"
        
        self.finder = MinCutFinder(self.uri, self.user, self.password)
        try:
            self.finder.connect()
            # Create test graph if needed
            self._create_test_graph()
        except Exception as e:
            logger.error(f"Error setting up test: {str(e)}")
            self.skipTest(f"Could not connect to Neo4j: {str(e)}")
    
    def tearDown(self):
        """Clean up test database."""
        if hasattr(self, 'finder') and self.finder:
            try:
                # Clean up test graph
                self._clean_test_graph()
            except Exception as e:
                logger.warning(f"Error cleaning up: {str(e)}")
            finally:
                self.finder.close()
    
    def _create_test_graph(self):
        """Create a sample graph for testing the min-cut algorithm."""
        with self.finder.driver.session() as session:
            # Check if the test graph already exists
            result = session.run("MATCH (n:TestNode) RETURN count(n) as count")
            count = result.single()["count"]
            
            if count > 0:
                logger.info("Test graph already exists, skipping creation")
                return
            
            # Create a simple graph with a known min-cut
            # The graph is a modified version of a diamond graph with additional edges
            #
            #      (2)---(3)
            #     /|     /|
            #    / |    / |
            #   /  |   /  |
            # (1)  |  /   |
            #   \  | /    |
            #    \ |/     |
            #     (4)---(5)
            #
            # Min-cut between nodes 1 and 5 should be edges (2,3) and (4,5)
            
            query = """
            CREATE 
              (n1:TestNode {name: 'Node1'}),
              (n2:TestNode {name: 'Node2'}),
              (n3:TestNode {name: 'Node3'}),
              (n4:TestNode {name: 'Node4'}),
              (n5:TestNode {name: 'Node5'}),
              (n1)-[:TEST_REL {weight: 1}]->(n2),
              (n1)-[:TEST_REL {weight: 1}]->(n4),
              (n2)-[:TEST_REL {weight: 1}]->(n3),
              (n2)-[:TEST_REL {weight: 1}]->(n4),
              (n3)-[:TEST_REL {weight: 1}]->(n4),
              (n3)-[:TEST_REL {weight: 1}]->(n5),
              (n4)-[:TEST_REL {weight: 1}]->(n5)
            RETURN n1, n5
            """
            
            result = session.run(query)
            record = result.single()
            
            logger.info("Created test graph for min-cut testing")
    
    def _clean_test_graph(self):
        """Remove the test graph."""
        with self.finder.driver.session() as session:
            query = """
            MATCH (n:TestNode)
            DETACH DELETE n
            """
            
            session.run(query)
            logger.info("Cleaned up test graph")
    
    def test_min_cut_basic(self):
        """Test the min-cut algorithm on a basic graph."""
        # First get node IDs
        with self.finder.driver.session() as session:
            query = """
            MATCH (start:TestNode {name: 'Node1'})
            MATCH (end:TestNode {name: 'Node5'})
            RETURN id(start) as start_id, id(end) as end_id
            """
            
            result = session.run(query)
            record = result.single()
            
            if not record:
                self.skipTest("Test nodes not found in database")
            
            start_id = record["start_id"]
            end_id = record["end_id"]
        
        # Find min-cut
        min_cut = find_min_cut(
            start_id,
            end_id,
            ["TEST_REL"],
            ["TestNode"],
            max_path_length=5,
            uri=self.uri,
            user=self.user,
            password=self.password
        )
        
        # Verify results
        self.assertIsNotNone(min_cut)
        self.assertEqual(len(min_cut), 2, "Expected 2 relationships in the min-cut")
        
        # Get the names of the nodes connected by the min-cut relationships
        # to verify we got the expected cut
        relationship_endpoints = []
        with self.finder.driver.session() as session:
            for rel in min_cut:
                rel_id = rel["id"]
                query = """
                MATCH (a)-[r]->(b) WHERE id(r) = $rel_id
                RETURN a.name as source_name, b.name as target_name
                """
                
                result = session.run(query, rel_id=rel_id)
                record = result.single()
                
                if record:
                    relationship_endpoints.append((record["source_name"], record["target_name"]))
        
        # Expected min-cut is the edges (Node2, Node3) and (Node4, Node5)
        expected_endpoints = [
            ("Node2", "Node3"),
            ("Node4", "Node5")
        ]
        
        # Sort both lists to make comparison reliable
        relationship_endpoints.sort()
        expected_endpoints.sort()
        
        for i, endpoint_pair in enumerate(relationship_endpoints):
            self.assertIn(
                endpoint_pair, 
                expected_endpoints, 
                f"Unexpected relationship in min-cut: {endpoint_pair}"
            )
        
        logger.info(f"Min-cut test passed with cuts: {relationship_endpoints}")


# Demo function to show usage in a more practical context
def demo_min_cut():
    """
    Demonstrate the usage of the min-cut algorithm with a simple example.
    
    This function creates a sample graph, finds the min-cut, and displays the results.
    """
    # Connect to Neo4j
    finder = MinCutFinder()
    try:
        finder.connect()
        
        # Create a sample graph
        with finder.driver.session() as session:
            # Clear any existing demo data
            session.run("MATCH (n:DemoNode) DETACH DELETE n")
            
            # Create a graph representing a network
            query = """
            CREATE 
              (a:DemoNode {name: 'A'}),
              (b:DemoNode {name: 'B'}),
              (c:DemoNode {name: 'C'}),
              (d:DemoNode {name: 'D'}),
              (e:DemoNode {name: 'E'}),
              (f:DemoNode {name: 'F'}),
              (g:DemoNode {name: 'G'}),
              (a)-[:CONNECTS {capacity: 3}]->(b),
              (a)-[:CONNECTS {capacity: 5}]->(d),
              (b)-[:CONNECTS {capacity: 2}]->(c),
              (b)-[:CONNECTS {capacity: 3}]->(e),
              (c)-[:CONNECTS {capacity: 4}]->(g),
              (d)-[:CONNECTS {capacity: 2}]->(e),
              (e)-[:CONNECTS {capacity: 1}]->(c),
              (e)-[:CONNECTS {capacity: 4}]->(f),
              (f)-[:CONNECTS {capacity: 6}]->(g)
            RETURN a, g
            """
            
            result = session.run(query)
            record = result.single()
            
            # Get node IDs for source and target
            query = """
            MATCH (source:DemoNode {name: 'A'})
            MATCH (target:DemoNode {name: 'G'})
            RETURN id(source) as source_id, id(target) as target_id
            """
            
            result = session.run(query)
            record = result.single()
            
            source_id = record["source_id"]
            target_id = record["target_id"]
        
        # Find the min-cut
        min_cut = finder.find_min_cut(
            source_id,
            target_id,
            ["CONNECTS"],
            ["DemoNode"],
            max_path_length=5
        )
        
        # Display results
        print("\n===== Min-Cut Demo =====")
        print(f"Found {len(min_cut)} relationships in the min-cut:")
        
        with finder.driver.session() as session:
            for i, rel in enumerate(min_cut):
                rel_id = rel["id"]
                query = """
                MATCH (a)-[r]->(b) WHERE id(r) = $rel_id
                RETURN a.name as source, b.name as target, r.capacity as capacity
                """
                
                result = session.run(query, rel_id=rel_id)
                record = result.single()
                
                print(f"{i+1}. {record['source']} -> {record['target']} (Capacity: {record['capacity']})")
        
        print("\nThese relationships represent the minimum cut in the network.")
        print("Removing these edges would disconnect the source from the target")
        print("with the minimum possible capacity reduction.")
        
    except Exception as e:
        print(f"Error in demo: {str(e)}")
    finally:
        finder.close()


if __name__ == "__main__":
    print("Running min-cut algorithm tests...")
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
    
    print("\nRunning min-cut demo...")
    try:
        demo_min_cut()
    except Exception as e:
        print(f"Demo failed: {str(e)}")
        print("Ensure Neo4j is running with APOC and GDS plugins installed.")
