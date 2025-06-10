# Neo4j Min-Cut Implementation

This project implements a minimum cut algorithm using Neo4j, the APOC plugin, and the Graph Data Science (GDS) library. It finds the minimum cut between two nodes in an undirected graph by leveraging Neo4j's graph capabilities.

## Overview

The implementation finds the minimum cut between two nodes using the following approach:

1. Find all edge-disjoint paths between the start and end nodes using `apoc.path.expandConfig` with `RELATIONSHIP_GLOBAL` uniqueness
2. Create a GDS graph projection of the original graph, but with the relationships in these paths removed
3. Run the Weakly Connected Components (WCC) algorithm to identify the components
4. Identify relationships in the original paths that cross between components (these form the min-cut)
5. Clean up resources by properly dropping the GDS projection when it's no longer needed

## Requirements

- Neo4j Database (5.0+)
- APOC Plugin
- Graph Data Science (GDS) Library
- Python 3.6+
- `neo4j` Python driver
- `neo4j-gds` Python client

## Installation

1. Install the required Python packages:

```bash
pip install -r requirements.txt
```

2. Ensure your Neo4j instance has the APOC and GDS plugins installed.

## Usage

### Basic Usage

```python
from mincut import find_min_cut

# Find the minimum cut
min_cut = find_min_cut(
    start_node_id=123,               # ID of the start node
    end_node_id=456,                 # ID of the end node
    relationship_types=["CONNECTS"],  # Types of relationships to consider
    node_labels=["Node"],            # Types of nodes to consider
    max_path_length=10,              # Maximum path length
    uri="bolt://localhost:7687",     # Neo4j connection URI
    user="neo4j",                    # Neo4j username
    password="password"              # Neo4j password
)

# The result is a list of relationship objects that form the min-cut
for rel in min_cut:
    print(f"Relationship ID: {rel['id']}, From: {rel['source']}, To: {rel['target']}, Type: {rel['type']}")
```

### Advanced Usage

For more control, you can use the `MinCutFinder` class directly:

```python
from mincut import MinCutFinder

# Create a finder instance
finder = MinCutFinder(uri="bolt://localhost:7687", user="neo4j", password="password")

try:
    # Connect to Neo4j
    finder.connect()
    
    # Find the minimum cut
    min_cut = finder.find_min_cut(
        start_node_id=123,
        end_node_id=456,
        relationship_types=["CONNECTS"],
        node_labels=["Node"],
        max_path_length=10
    )
    
    # Process the results
    print(f"Found {len(min_cut)} relationships in the min-cut")
    
finally:
    # Always close the connection
    finder.close()
```

## Type Handling and Neo4j Compatibility


### Neo4j Version Compatibility

This implementation is compatible with newer versions of Neo4j (4.0+) by using:

- `elementId()` instead of the deprecated `id()` function for node and relationship identification
- Current GDS API for graph projection and algorithm execution
- Proper cleanup of GDS projections without deprecated parameters

## Testing

The project includes test cases that demonstrate the functionality with a sample graph:

```bash
python test_mincut.py
```

This will run the test cases and a demo that creates a sample graph and finds the min-cut.

## Algorithm Details

The implementation follows the principles of the max-flow min-cut theorem, which states that the maximum flow from a source to a sink in a network equals the minimum capacity of any cut separating the source from the sink.

Our specific approach:

1. **Path Identification**: Finds all edge-disjoint paths between start and end nodes using APOC's path expansion capabilities
2. **Graph Projection**: Creates an undirected GDS graph projection excluding the path relationships
   - Uses efficient node filtering with the `get_node_condition` helper method
   - Converts all IDs to integers for consistent type handling
3. **Component Analysis**: Runs the WCC algorithm to identify connected components after path removal
4. **Min-Cut Identification**: Finds edges that cross between the component containing the start node and the component containing the end node
5. **Resource Management**: Properly releases resources by dropping the GDS projection after use

## Resource Management

The implementation ensures proper resource management by:

- Explicitly dropping any existing GDS projections before creating new ones
- Using the current GDS API without deprecated parameters
- Cleaning up resources even when exceptions occur through proper try/finally blocks

## Helper Methods

The implementation provides several helper methods for improved functionality:

- `get_node_condition`: Creates a Cypher WHERE clause for filtering nodes by labels
- `_get_component_id`: Retrieves the component ID for a given node in the GDS projection
- `_drop_gds_projection`: Properly drops a GDS graph projection when it's no longer needed

## Limitations

- The algorithm assumes an undirected graph
- Performance may degrade with very large graphs or when many paths exist between the start and end nodes
- The Neo4j instance must have sufficient memory to handle the graph projections

## License

This project is available under the MIT License.
