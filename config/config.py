"""
Configuration module for Flight Ticket Sales Dashboard
Manages database connections and credentials through environment variables
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Neo4j Database Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://e4d78cf5.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# MongoDB Database Configuration
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mongodb:akuvalent@cluster0.zq9clry.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "ticketing")

# Application Configuration
APP_TITLE = "Flight Ticket Sales & Performance Analysis Dashboard"
APP_ICON = "chart_with_upwards_trend"
PAGE_LAYOUT = "wide"

# Default Analysis Period
DEFAULT_START_DATE = "2023-03-10"
DEFAULT_END_DATE = "2023-04-09"
