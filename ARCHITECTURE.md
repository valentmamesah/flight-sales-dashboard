# Technical Architecture Documentation

## System Overview

The Flight Sales Dashboard is a modern web application built with Streamlit that provides real-time analysis of flight ticket sales data stored in MongoDB and Neo4j databases.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit Web UI                           │
│  ┌──────────────┬──────────────┬──────────────┬────────────┐ │
│  │  Tab 1: S1   │  Tab 2: S2   │  Tab 3: Perf │  Tab 4-5   │ │
│  └──────────────┴──────────────┴──────────────┴────────────┘ │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  ┌──────────────────────────────────────────────────────────┤
│  │  app.py - Main Application Logic & UI Rendering           │
│  └──────────────────────────────────────────────────────────┘
│  ┌──────────────────────────────────────────────────────────┤
│  │  analytics.py - Business Logic & Query Execution          │
│  └──────────────────────────────────────────────────────────┘
│  ┌──────────────────────────────────────────────────────────┤
│  │  db_utils.py - Database Operations & Connection Mgmt      │
│  └──────────────────────────────────────────────────────────┘
│  ┌──────────────────────────────────────────────────────────┤
│  │  config.py - Configuration & Environment Variables        │
│  └──────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────┘
         ↓                                         ↓
    ┌─────────┐                             ┌──────────┐
    │ MongoDB │                             │  Neo4j   │
    │  Atlas  │                             │  AuraDB  │
    └─────────┘                             └──────────┘
```

## Component Descriptions

### 1. app.py (Main Application)
**Responsibility**: Orchestrate UI and user interactions

**Key Functions**:
- `configure_page()`: Set up Streamlit page settings
- `render_sidebar_controls()`: Build sidebar configuration interface
- `render_tab_*()`: Render individual tab content
- `main()`: Main application entry point

**Dependencies**: 
- Streamlit, Plotly, Pandas
- db_utils, analytics, config modules

### 2. analytics.py (Analytics Engine)
**Responsibility**: Execute queries and generate insights

**Key Functions**:
- `get_sales_by_date()`: Calculate daily sales aggregates
- `run_scenario_without_optimization()`: Execute unoptimized queries
- `run_scenario_with_optimization()`: Execute optimized queries
- `generate_insights()`: Create business intelligence outputs

**Query Patterns**:
- Aggregation pipelines for MongoDB
- Cypher queries for Neo4j
- Data joining and merging

### 3. db_utils.py (Database Layer)
**Responsibility**: Manage database connections and operations

**Key Functions**:
- `init_connections()`: Create MongoDB and Neo4j connections
- `create_mongodb_indexes()`: Create database indexes
- `drop_mongodb_indexes()`: Remove indexes for testing
- `create_neo4j_indexes()`: Create Neo4j indexes
- `drop_neo4j_indexes()`: Remove Neo4j indexes

**Connection Management**:
- Pooled connections for efficiency
- Error handling and timeout management
- Connection verification

### 4. config.py (Configuration)
**Responsibility**: Centralize configuration management

**Features**:
- Environment variable loading
- Default values for all settings
- Separation of secrets and application config

## Data Flow

### Analysis Execution Flow

```
User Action (Run Scenario)
    ↓
app.py - Capture User Input & Date Range
    ↓
db_utils.py - Initialize Database Connections
    ↓
analytics.py - Execute Query Scenarios
    ├── Get Sales by Date
    ├── Calculate Total Sales
    ├── Fetch Routes from Neo4j
    └── Calculate Sales per Route
    ↓
app.py - Format Results & Display Visualizations
    ↓
Streamlit - Render UI to User
```

### Query Optimization Comparison

#### Without Optimization Flow
```
For each route in routes:
    Execute MongoDB query for that route
    Aggregate results
    Store in results array
→ O(n) database round trips
→ No indexes used
→ Individual query parsing overhead
```

#### With Optimization Flow
```
Prepare list of all route origins and destinations
Execute single MongoDB aggregation pipeline
    Filter by date and route list
    Group by origin and destination
    Calculate aggregates
→ O(1) database round trip
→ Indexes used for filtering
→ Single query plan
```

## Database Schema

### MongoDB Collections

**Collection: orders**
```javascript
{
  "_id": ObjectId,
  "order_id": String,
  "customer_id": String,
  "flight_id": String,
  "origin": String,           // Indexed
  "destination": String,       // Indexed
  "depart_date": Date,         // Indexed
  "departure_time": String,
  "arrival_time": String,
  "class": String,            // Economy, Business, etc
  "passengers": Number,
  "price_per_person": Number,
  "total_price": Number,      // Used for aggregation
  "booking_date": Date,
  "status": String            // Confirmed, Cancelled, etc
}
```

**Indexes**:
- `idx_depart_date`: `{depart_date: 1}`
- `idx_flight_id`: `{flight_id: 1}`
- `idx_origin_dest_date`: `{origin: 1, destination: 1, depart_date: 1}`
- `idx_fp_id`: On flight_prices collection `{id: 1}`

**Collection: flight_prices**
```javascript
{
  "_id": ObjectId,
  "id": String,               // Indexed
  "flight_id": String,
  "date": Date,
  "price": Number,
  "currency": String
}
```

### Neo4j Graph

**Node: Airport**
```
(:Airport {
  airport_code: String,       // Indexed
  airport_name: String,
  city: String,
  country: String,
  latitude: Float,
  longitude: Float
})
```

**Relationship: CONNECTED_TO**
```
(origin)-[:CONNECTED_TO {
  distance_km: Float,         // Indexed
  flight_time_hr: Float,      // Indexed
  frequency_per_week: Integer,
  airlines: [String]
}]->(destination)
```

**Indexes**:
- `idx_airport_code`: On Airport.airport_code
- `idx_ct_distance_time`: On CONNECTED_TO relationship properties

## Performance Optimization Strategies

### 1. Database Indexing
- Compound indexes on frequently filtered fields
- Indexes on sorting fields
- Regular index maintenance and statistics updates

### 2. Query Batching
- Convert N individual queries to 1 batch query
- Use MongoDB aggregation pipeline for complex operations
- Leverage database-level filtering instead of application-level

### 3. Connection Pooling
- Reuse database connections
- Manage connection lifecycle
- Handle connection timeouts gracefully

### 4. Query Filtering
- Apply WHERE clauses in Neo4j queries
- Use $match early in aggregation pipelines
- Limit result sets with LIMIT clauses

### 5. Data Caching
- Streamlit's built-in caching for expensive operations
- Session state for keeping analysis results in memory
- Smart cache invalidation on parameter changes

## Error Handling Strategy

```
Database Connection
├── Connection Timeout
│   └── Display user-friendly error message
├── Authentication Failed
│   └── Check credentials in .env
└── Database Unreachable
    └── Check network connectivity

Query Execution
├── Invalid Data Type
│   └── Handle with try-except
├── Empty Result Set
│   └── Return empty DataFrame with message
└── Query Timeout
    └── Extend timeout or simplify query

Data Processing
├── Missing Fields
│   └── Fill with defaults or skip rows
├── Type Conversion
│   └── Safe conversion with error handling
└── Calculation Error
    └── Log error and display message
```

## Security Considerations

### Credentials Management
- Never commit .env file to repository
- Use environment variables for all secrets
- Rotate credentials regularly
- Use read-only roles where possible

### Data Protection
- Use HTTPS for cloud database connections
- Implement network access lists
- Regular backups of critical data
- Encrypt sensitive data at rest

### Application Security
- Validate all user inputs (dates, selections)
- Implement rate limiting for API calls
- Monitor for suspicious activities
- Regular dependency updates

## Scalability Considerations

### Current Capacity
- Handles millions of documents in MongoDB
- Supports complex queries with proper indexing
- Suitable for daily/weekly analysis patterns

### Scaling Strategies
1. **Database Level**
   - Sharding for very large datasets
   - Read replicas for query distribution
   - Query optimization and tuning

2. **Application Level**
   - Caching layer (Redis)
   - Asynchronous query execution
   - Background job processing

3. **Infrastructure Level**
   - Load balancing for multiple Streamlit instances
   - CDN for static assets
   - Containerization with Docker

## Monitoring and Logging

### Metrics to Track
- Query execution times
- Database connection health
- API response times
- Error rates and types
- User activity patterns

### Logging Strategy
- Structured logging with timestamps
- Log levels: DEBUG, INFO, WARNING, ERROR
- Log to file and stdout
- Regular log rotation and cleanup

## Testing Strategy

### Unit Tests
```python
def test_sales_by_date_aggregation():
    # Test date range filtering
    # Test aggregation logic
    # Test data type conversion

def test_database_index_creation():
    # Test index creation without errors
    # Test index actually improves query performance
    # Test index cleanup
```

### Integration Tests
```python
def test_end_to_end_analysis():
    # Test full scenario execution
    # Verify database connectivity
    # Check output data structure

def test_optimization_impact():
    # Compare scenario 1 vs 2 timing
    # Verify optimization improves performance
    # Check result consistency
```

### Performance Tests
```python
def test_query_performance():
    # Measure execution times
    # Verify < timeout duration
    # Check resource utilization
```

## Deployment Considerations

### Local Deployment
- Simple setup for development and testing
- Direct database access required
- Manual credential configuration

### Cloud Deployment (Streamlit Cloud)
- Automatic scaling and management
- GitHub integration for CI/CD
- Environment variables via UI
- Custom domain support

### Docker Deployment
- Containerized execution
- Portable across environments
- Easy orchestration with Docker Compose
- Production-ready deployment

## Future Architecture Improvements

1. **Microservices**
   - Separate query service from UI
   - Independent scaling capabilities
   - Better fault isolation

2. **Caching Layer**
   - Redis for query result caching
   - Session-based cache invalidation
   - Distributed cache support

3. **Real-time Updates**
   - WebSocket for live data streaming
   - Event-driven architecture
   - Real-time dashboard updates

4. **Advanced Analytics**
   - Machine learning model integration
   - Predictive analytics
   - Anomaly detection

---

For implementation details and code examples, refer to individual module docstrings.
