"""
Core module containing database operations and analytics functions
"""

from .database import (
    init_connections,
    create_mongodb_indexes,
    drop_mongodb_indexes,
    create_neo4j_indexes,
    drop_neo4j_indexes
)

from .analytics import (
    run_scenario_without_optimization,
    run_scenario_with_optimization,
    generate_insights
)

__all__ = [
    'init_connections',
    'create_mongodb_indexes',
    'drop_mongodb_indexes',
    'create_neo4j_indexes',
    'drop_neo4j_indexes',
    'run_scenario_without_optimization',
    'run_scenario_with_optimization',
    'generate_insights'
]
