"""
Neo4j Min-Cut Algorithm Implementation

This module provides functionality to find the minimum cut between two nodes in an undirected graph
using Neo4j and the Graph Data Science (GDS) library.
"""

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
import logging
import time

# Configure logging
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.CRITICAL + 1, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

class MinCutFinder:
    """Class for finding minimum cuts between nodes in a Neo4j graph."""
    
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password"):
        """
        Initialize the MinCutFinder with Neo4j connection parameters.
        
        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
    
    def connect(self):
        """Establish connection to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()["test"]
            logger.info(f"Successfully connected to Neo4j at {self.uri}")
            
            # Verify APOC and GDS plugins
            self._verify_plugins()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise ConnectionError(f"Could not connect to Neo4j: {str(e)}")
    
    def _verify_plugins(self):
        """Verify that required Neo4j plugins (APOC and GDS) are installed."""
        with self.driver.session() as session:
            # Check APOC
            try:
                session.run("CALL apoc.help('path')")
                logger.info("APOC plugin is available")
            except Neo4jError:
                logger.error("APOC plugin is not available")
                raise RuntimeError("APOC plugin is required but not available")
            
            # Check GDS
            try:
                session.run("CALL gds.list()")
                logger.info("GDS plugin is available")
            except Neo4jError:
                logger.error("GDS plugin is not available")
                raise RuntimeError("GDS plugin is required but not available")
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def find_min_cut(
        self,
        start_node_id,
        end_node_id,
        relationship_types,
        node_labels,
        max_path_length=10
    ):
        """
        Find the minimum cut between start and end nodes in an undirected graph.
        
        Args:
            start_node_id: ID of the start node
            end_node_id: ID of the end node
            relationship_types: List of relationship types to traverse
            node_labels: List of node labels to consider
            max_path_length: Maximum path length to consider
            
        Returns:
            List of relationship IDs that form the minimum cut
        """
        if not self.driver:
            self.connect()
        
        # Dictionary to store timing information
        timing = {}
        start_time_total = time.time()
        
        try:
            start_node_id = start_node_id.strip()
            end_node_id = end_node_id.strip()
            
            # Step 1: Find edge-disjoint paths
            start_time = time.time()
            paths = self._find_edge_disjoint_paths(
                start_node_id, 
                end_node_id, 
                relationship_types, 
                node_labels, 
                max_path_length
            )
            timing['1. Find edge-disjoint paths'] = time.time() - start_time
            
            if not paths:
                logger.warning("No paths found between start and end nodes")
                return []
            
            # Step 2: Extract all relationships from paths
            start_time = time.time()
            path_relationships = self._extract_relationships_from_paths(paths)
            timing['2. Extract relationships'] = time.time() - start_time
            
            # Step 3: Create GDS projection with path relationships removed
            start_time = time.time()
            projection_name = self._create_gds_projection_without_paths(
                path_relationships, 
                relationship_types, 
                node_labels
            )
            timing['3. Create GDS projection'] = time.time() - start_time
            
            # Step 4: Run WCC algorithm
            start_time = time.time()
            self._run_wcc_algorithm(projection_name)
            timing['4. Run WCC algorithm'] = time.time() - start_time
            
            # Step 5: Identify min-cut relationships
            start_time = time.time()
            min_cut = self._identify_min_cut_relationships(
                 path_relationships, 
                start_node_id, 
                end_node_id
            )
            timing['5. Identify min-cut'] = time.time() - start_time
            
            # Step 6: Clean up GDS projection
            start_time = time.time()
            self._drop_gds_projection(projection_name)
            timing['6. Drop GDS projection'] = time.time() - start_time
            
            # Calculate total time
            timing['Total'] = time.time() - start_time_total
            
            # Print timing summary if logging is enabled
            self._print_timing_summary(timing)
            
            return min_cut
            
        except Exception as e:
            logger.error(f"Error finding min-cut: {str(e)}")
            raise
    
    def _find_edge_disjoint_paths(
        self, 
        start_node_id, 
        end_node_id, 
        relationship_types, 
        node_labels, 
        max_path_length
    ):
        """
        Find all edge-disjoint paths between start and end nodes using APOC.
        
        Returns:
            List of paths, where each path is a list of nodes and relationships
        """
        logger.info(f"Finding edge-disjoint paths from node {start_node_id} to {end_node_id}")
        
        # Create relationship pattern for undirected traversal
        # Format: REL1|REL2|...
        rel_pattern = ""
        if relationship_types:
            rel_pattern = "|".join(relationship_types) #Do we need to exclude start and end nodes?
        else:
            rel_pattern = ""
        # Any relationship in any direction
        
        # Create node labels pattern
        # Format: "LABEL1|LABEL2|..."
        label_pattern = ""
        if node_labels:
            label_pattern = "|".join(node_labels)
        else:
            label_pattern = ""  # Any node
    
        with self.driver.session() as session:
            query = """
            MATCH (start) WHERE elementId(start) = $start_id
            MATCH (end) WHERE elementId(end) = $end_id
            CALL apoc.path.expandConfig(start, {
                relationshipFilter: $rel_pattern,
                labelFilter: $label_pattern,
                uniqueness: "RELATIONSHIP_GLOBAL",
                maxLevel: $max_length,
                terminatorNodes: [end]
            })
            YIELD path
            RETURN path
            """            
            result = session.run(
                query,
                start_id=start_node_id,
                end_id=end_node_id,
                rel_pattern=rel_pattern,
                label_pattern=label_pattern,
                max_length=max_path_length
            )
            
            paths = [record["path"] for record in result]
            logger.info(f"Found {len(paths)} edge-disjoint paths")
            
            return paths
    
    def _extract_relationships_from_paths(self, paths):
        """
        Extract all relationships from the given paths.
        
        Returns:
            Set of relationship IDs
        """
        relationship_ids = set()
        
        for path in paths:
            for rel in path.relationships:
                relationship_ids.add(rel.element_id)
        
        logger.info(f"Extracted {len(relationship_ids)} unique relationships from paths")
        return relationship_ids
    
    def get_node_condition(self, variable:str, node_labels:list):
        return ' OR '.join([f'{variable}:{label}' for label in node_labels])


    def _create_gds_projection_without_paths(
        self, 
        path_relationships, 
        relationship_types, 
        node_labels
    ):
        """
        Create a GDS graph projection without the relationships in the paths using Cypher projection.
        
        Returns:
            Name of the created GDS projection
        """
        projection_name = "min_cut_projection"
        
        # Convert node labels to a list if it's a string
        if isinstance(node_labels, str):
            node_labels = [node_labels]
        
        # Convert relationship types to a list if it's a string
        if isinstance(relationship_types, str):
            relationship_types = [relationship_types]
        self._drop_gds_projection(projection_name)  # Ensure clean state before creating projection
        with self.driver.session() as session:

            # Convert path relationships to a list and ensure they are integers
            path_rel_list = [rel_id for rel_id in path_relationships] if path_relationships else []
            
            rel_conditions = []
            if relationship_types:
                for rel_type in relationship_types:
                    rel_conditions.append(f"type(r) = '{rel_type}'")
                rel_type_condition = " OR ".join(rel_conditions) if rel_conditions else "true"
            # Build relationship query that excludes the path relationships
           
            project_query = f"""
            MATCH (a) 
            OPTIONAL MATCH (a)-[r]->(b)
            WHERE ({self.get_node_condition('a', node_labels)}) AND ({self.get_node_condition('b', node_labels)}) AND ({rel_type_condition})
            AND NOT elementId(r) IN $excluded_rel_ids
            WITH a AS source, b as target, type(r) AS type
            """
            query = f"""
            cypher runtime=parallel
            {project_query}
            WITH gds.graph.project(
                '{projection_name}',
                source, 
                target,
                {{}},
                {{undirectedRelationshipTypes: ["*"]}}
            )
            as g 
            RETURN g.graphName AS graph, g.nodeCount AS nodes, g.relationshipCount AS rels
            """

            result = session.run(
                query,
                projection_name=projection_name,
                excluded_rel_ids=path_rel_list
            )
            r = result.single()
            logger.info(r.values())
            logger.info(f"Created GDS projection: {projection_name}")
            
            return projection_name
    
    def _run_wcc_algorithm(self, projection_name):
        """
        Run the Weakly Connected Components algorithm on the GDS projection using mutate mode.
        This is more efficient for large graphs as it doesn't require storing the entire
        component mapping in memory.
        
        Returns:
            Dictionary mapping node IDs to their component IDs for compatibility
        """
        logger.info(f"Running WCC algorithm on projection: {projection_name}")
        
        with self.driver.session() as session:
            query = """
            CALL gds.wcc.mutate($projection_name, {
                mutateProperty: 'componentId'
            })
            YIELD componentCount
            RETURN componentCount
            """
            
            result = session.run(query, projection_name=projection_name)
            component_count = result.single()["componentCount"]
            logger.info(f"WCC algorithm found {component_count} components")
            if not component_count > 1:
                logger.warning("WCC algorithm found only one component, no min-cut exists")
                raise ValueError("No min-cut exists between the specified nodes")

            print(f"WCC algorithm found {component_count} components")
            
           
    
    def _drop_gds_projection(self, projection_name):
        """
        Drop the GDS graph projection when it's no longer needed.
        
        Args:
            projection_name: Name of the GDS projection to drop
        """
        logger.info(f"Dropping GDS projection: {projection_name}")
        
        with self.driver.session() as session:
            try:
                # Updated to use the current GDS API without deprecated parameters
                query = "CALL gds.graph.drop($projection_name)"
                session.run(query, projection_name=projection_name)
                logger.info(f"Successfully dropped GDS projection: {projection_name}")
            except Neo4jError as e:
                logger.warning(f"Failed to drop GDS projection '{projection_name}': {str(e)}")
    
    def _print_timing_summary(self, timing):
        """
        Print a summary of the execution times for each step of the min-cut algorithm.
        
        Args:
            timing: Dictionary mapping step names to execution times in seconds
        """
        # Only print timing information if logging is enabled at INFO level or lower
        if logger.level <= logging.INFO:
            total_time = timing.get('Total', 0)
            if total_time == 0:
                return
                
            print("\n=== Min-Cut Timing Summary ===")
            print(f"{'Step':<30} {'Time (s)':<10} {'Percentage':<10}")
            print("-" * 55)
            
            # Print each step's timing
            for step, duration in timing.items():
                if step != 'Total':
                    percentage = (duration / total_time) * 100
                    print(f"{step:<30} {duration:.4f}s    {percentage:.1f}%")
            
            # Print total at the end
            print("-" * 55)
            print(f"{'Total':<30} {total_time:.4f}s    100.0%\n")
    
    def get_element_id_from_id(self, node_id):
        """
        Get the element ID for a given node ID.
        
        Args:
            node_id: ID of the node to query
            
        Returns:
            Element ID of the node
        """
        if not self.driver:
            self.connect()
        with self.driver.session() as session:
            query = "MATCH (n) WHERE id(n) = $node_id RETURN elementId(n) AS elementId"
            result = session.run(query, node_id=node_id)
            return result.single()["elementId"]

    def _get_component_id(self, node_id, projection_name):
        """
        Get the component ID for a given node in the GDS projection.
        
        Args:
            node_id: ID of the node to query
            projection_name: Name of the GDS projection
            
        Returns:
            Component ID for the node
        """
        with self.driver.session() as session:
            query = """
            match (n) where elementId(n) = $node_id
            RETURN gds.util.nodeProperty($projection_name, n, 'componentId') AS componentId
            """
            result = session.run(query, projection_name=projection_name, node_id=node_id)
            return result.single()["componentId"]

    def _identify_min_cut_relationships(
        self, 
        path_relationships, 
        start_node_id, 
        end_node_id, 
        projection_name="min_cut_projection"
    ):
        """
        Identify relationships in the original paths that form the min-cut.
        Uses the componentId property stored in the graph directly when possible.
        
        Returns:
            List of relationship objects that form the min-cut
        """
        logger.info("Identifying min-cut relationships")
        
        # Find relationships that cross between components
        min_cut_relationships = []
        start_component = self._get_component_id(start_node_id, projection_name)
        end_component = self._get_component_id(end_node_id, projection_name)

        if start_component is None:
            logger.error(f"Start node {start_node_id} not found in component mapping")
            raise ValueError(f"Start node {start_node_id} not found in component mapping")
    
        if end_component is None:
            logger.error(f"End node {end_node_id} not found in component mapping")
            raise ValueError(f"End node {end_node_id} not found in component mapping")
    
        # If start and end are in the same component, there's no min-cut
        if start_component == end_component:
            logger.warning("Start and end nodes are in the same component, no min-cut exists")
            return []
    
        with self.driver.session() as session:
            logger.info(f"Start component: {start_component}, End component: {end_component}")

            # Convert relationship IDs to integers for consistency
            path_rel_list = [rel_id for rel_id in path_relationships]
            
            # Find edges that cross between components more efficiently
            # by directly querying the projection's component IDs
            query = f"""
            MATCH (a)-[r]->(b) 
            WHERE elementId(r) IN $rel_ids AND
            gds.util.nodeProperty('{projection_name}', a, 'componentId') in [$start_component, $end_component] AND
            gds.util.nodeProperty('{projection_name}', b, 'componentId') in [$start_component, $end_component] AND
            gds.util.nodeProperty('{projection_name}', a, 'componentId') <> gds.util.nodeProperty('{projection_name}', b, 'componentId')
            
            RETURN elementId(r) as rel, elementId(a) as source, elementId(b) as target
            """
            # We need to batch large lists to avoid query size limits
            batch_size = 1000
            for i in range(0, len(path_rel_list), batch_size):
                batch = path_rel_list[i:i+batch_size]
                
                result = session.run(
                    query, 
                    rel_ids=batch,
                    start_component=start_component,
                    end_component=end_component
                )
                
                for record in result:
                    min_cut_relationships.append({
                        "id": record["rel"],
                        "source": record["source"],
                        "target": record["target"]})
        logger.info(f"Identified {len(min_cut_relationships)} relationships in the min-cut")
        return min_cut_relationships

def find_min_cut(
    start_node_id,
    end_node_id,
    relationship_types,
    node_labels,
    max_path_length=10,
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password",
    ids_are_node_ids=False
):
    """
    Find minimum cut between start and end nodes in an undirected graph using edge-disjoint paths.
    
    Args:
        start_node_id: ID of the start node
        end_node_id: ID of the end node
        relationship_types: List of relationship types to traverse
        node_labels: List of node labels to consider
        max_path_length: Maximum path length to consider
        uri: Neo4j connection URI
        user: Neo4j username
        password: Neo4j password
        
    Returns:
        List of relationship IDs that form the minimum cut
    """
    finder = MinCutFinder(uri, user, password)
    if ids_are_node_ids:
        start_node_id = finder.get_element_id_from_id(start_node_id)
        end_node_id = finder.get_element_id_from_id(end_node_id)

    try:
        return finder.find_min_cut(
            start_node_id,
            end_node_id,
            relationship_types,
            node_labels,
            max_path_length
        )
    finally:
        finder.close()
