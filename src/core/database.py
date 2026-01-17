"""
Database utilities module
Handles database connections and operations for MongoDB and Neo4j
"""

import streamlit as st
from pymongo import MongoClient
from neo4j import GraphDatabase
from config.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MONGO_URI, MONGO_DB_NAME


def init_connections():
    """
    Initialize connections to MongoDB and Neo4j databases
    
    Returns:
        tuple: (neo4j_driver, mongo_client, mongo_db) or (None, None, None) if connection fails
    """
    try:
        # Neo4j connection initialization
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        
        # MongoDB connection initialization
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        mongo_db = mongo_client[MONGO_DB_NAME]
        
        return driver, mongo_client, mongo_db
    except Exception as e:
        st.error(f"Error connecting to databases: {e}")
        return None, None, None


def create_mongodb_indexes(mongo_db):
    """
    Create indexes on MongoDB collections for improved query performance
    
    Args:
        mongo_db: MongoDB database instance
        
    Returns:
        bool: True if indexes created successfully, False otherwise
    """
    orders = mongo_db["orders"]
    flight_prices = mongo_db["flight_prices"]

    try:
        # Create single field indexes
        orders.create_index([("depart_date", 1)], name="idx_depart_date")
        orders.create_index([("flight_id", 1)], name="idx_flight_id")
        
        # Create compound index for route-date queries
        orders.create_index(
            [("origin", 1), ("destination", 1), ("depart_date", 1)],
            name="idx_origin_dest_date"
        )
        
        flight_prices.create_index([("id", 1)], name="idx_fp_id")
        return True
    except Exception as e:
        st.error(f"Error creating MongoDB indexes: {e}")
        return False


def drop_mongodb_indexes(mongo_db):
    """
    Drop existing MongoDB indexes (for testing/cleanup)
    
    Args:
        mongo_db: MongoDB database instance
        
    Returns:
        bool: True if indexes dropped successfully, False otherwise
    """
    orders = mongo_db["orders"]
    flight_prices = mongo_db["flight_prices"]

    try:
        orders.drop_index("idx_depart_date")
        orders.drop_index("idx_flight_id")
        orders.drop_index("idx_origin_dest_date")
        flight_prices.drop_index("idx_fp_id")
        return True
    except Exception as e:
        st.error(f"Error dropping MongoDB indexes: {e}")
        return False


def create_neo4j_indexes(tx):
    """
    Create indexes on Neo4j database for improved query performance
    
    Args:
        tx: Neo4j transaction object
    """
    # Create index on airport codes for faster lookups
    tx.run("""
        CREATE INDEX idx_airport_code IF NOT EXISTS
        FOR (a:Airport)
        ON (a.airport_code);
    """)
    
    # Create index on route distance and flight time
    tx.run("""
        CREATE INDEX idx_ct_distance_time IF NOT EXISTS
        FOR ()-[r:CONNECTED_TO]-()
        ON (r.distance_km, r.flight_time_hr);
    """)


def drop_neo4j_indexes(tx):
    """
    Drop existing Neo4j indexes (for testing/cleanup)
    
    Args:
        tx: Neo4j transaction object
    """
    tx.run("DROP INDEX idx_airport_code IF EXISTS")
    tx.run("DROP INDEX idx_ct_distance_time IF EXISTS")
