# API Reference Documentation

## Module: analytics.py

### Functions

#### `get_sales_by_date(orders_collection, start_date, end_date)`

Calculate daily sales aggregates within a specified date range.

**Parameters:**
- `orders_collection` (pymongo.collection.Collection): MongoDB orders collection
- `start_date` (datetime.datetime): Start date for analysis
- `end_date` (datetime.datetime): End date for analysis

**Returns:**
- `tuple`: (pandas.DataFrame, float) - DataFrame with columns [date, daily_sales, daily_orders] and query execution time

**Example:**
```python
from datetime import datetime
from analytics import get_sales_by_date

start_date = datetime(2023, 3, 10)
end_date = datetime(2023, 4, 9)
df_daily, execution_time = get_sales_by_date(orders_collection, start_date, end_date)

print(f"Query took {execution_time:.4f} seconds")
print(df_daily.head())
#         date  daily_sales  daily_orders
# 0 2023-03-10     1000000.0           100
# 1 2023-03-11     1200000.0           120
```

---

#### `run_scenario_without_optimization(orders_collection, driver, start_date, end_date)`

Execute analysis scenario without optimization (no indexes, individual queries).

**Parameters:**
- `orders_collection` (pymongo.collection.Collection): MongoDB orders collection
- `driver` (neo4j.driver.Driver): Neo4j database driver
- `start_date` (datetime.datetime): Start date for analysis
- `end_date` (datetime.datetime): End date for analysis

**Returns:**
- `dict`: Results dictionary containing:
  - `total_sales` (float): Total sales amount
  - `total_orders` (int): Total number of orders
  - `mongo_total_time` (float): Total sales query execution time
  - `daily_trend_time` (float): Daily trend query execution time
  - `neo4j_time` (float): Neo4j routes query execution time
  - `mongo_routes_time` (float): Routes sales query execution time
  - `df_daily` (DataFrame): Daily sales data
  - `df_sorted` (DataFrame): Routes sorted by sales

**Example:**
```python
from analytics import run_scenario_without_optimization

results = run_scenario_without_optimization(
    orders_collection, driver, start_date, end_date
)

print(f"Total Sales: Rp {results['total_sales']:,}")
print(f"Total Orders: {results['total_orders']:,}")
print(f"Total Execution Time: {results['mongo_routes_time']:.2f}s")
```

---

#### `run_scenario_with_optimization(orders_collection, driver, start_date, end_date)`

Execute analysis scenario with optimization (indexes, batch processing).

**Parameters:**
- `orders_collection` (pymongo.collection.Collection): MongoDB orders collection
- `driver` (neo4j.driver.Driver): Neo4j database driver
- `start_date` (datetime.datetime): Start date for analysis
- `end_date` (datetime.datetime): End date for analysis

**Returns:**
- `dict`: Same structure as scenario without optimization

**Optimizations Applied:**
- Composite indexes on (origin, destination, depart_date)
- Batch aggregation for route sales instead of individual queries
- Predicate filtering in Neo4j WHERE clause

**Example:**
```python
from analytics import run_scenario_with_optimization

results = run_scenario_with_optimization(
    orders_collection, driver, start_date, end_date
)

print(f"Total Sales: Rp {results['total_sales']:,}")
print(f"Batch Query Time: {results['mongo_routes_time']:.2f}s")
```

---

#### `generate_insights(results1, results2, period_days)`

Generate business intelligence insights from analysis results.

**Parameters:**
- `results1` (dict): Results from scenario without optimization
- `results2` (dict): Results from scenario with optimization  
- `period_days` (int): Number of days in analysis period

**Returns:**
- `list`: List of insight dictionaries with keys:
  - `type` (str): Insight type (performance, sales, trend, route, correlation, recommendation)
  - `title` (str): Insight title
  - `content` (str): Insight details and analysis

**Insight Types:**

| Type | Description |
|------|-------------|
| `performance` | Database optimization impact metrics |
| `sales` | Overall sales performance summary |
| `trend` | Daily sales trends and patterns |
| `route` | Best-performing routes analysis |
| `correlation` | Distance vs sales correlation |
| `recommendation` | Business actionable recommendations |

**Example:**
```python
from analytics import generate_insights

insights = generate_insights(results1, results2, period_days=31)

for insight in insights:
    print(f"[{insight['type'].upper()}] {insight['title']}")
    print(insight['content'])
    print()
```

---

## Module: db_utils.py

### Functions

#### `init_connections()`

Initialize connections to MongoDB and Neo4j databases.

**Parameters:** None

**Returns:**
- `tuple`: (neo4j_driver, mongo_client, mongo_db) or (None, None, None) on failure
- `neo4j_driver` (neo4j.driver.Driver): Neo4j driver instance
- `mongo_client` (pymongo.MongoClient): MongoDB client instance
- `mongo_db` (pymongo.database.Database): MongoDB database instance

**Example:**
```python
from db_utils import init_connections

driver, mongo_client, mongo_db = init_connections()

if driver and mongo_client:
    print("Connected successfully")
else:
    print("Connection failed")
```

**Errors Handled:**
- Connection timeout
- Authentication failure
- Network unreachability

---

#### `create_mongodb_indexes(mongo_db)`

Create indexes on MongoDB collections for query optimization.

**Parameters:**
- `mongo_db` (pymongo.database.Database): MongoDB database instance

**Returns:**
- `bool`: True if successful, False otherwise

**Indexes Created:**
- `idx_depart_date` on orders.depart_date
- `idx_flight_id` on orders.flight_id  
- `idx_origin_dest_date` on orders (origin, destination, depart_date)
- `idx_fp_id` on flight_prices.id

**Example:**
```python
from db_utils import create_mongodb_indexes

success = create_mongodb_indexes(mongo_db)
if success:
    print("Indexes created successfully")
```

---

#### `drop_mongodb_indexes(mongo_db)`

Drop MongoDB indexes (for testing non-optimized scenario).

**Parameters:**
- `mongo_db` (pymongo.database.Database): MongoDB database instance

**Returns:**
- `bool`: True if successful, False otherwise

**Example:**
```python
from db_utils import drop_mongodb_indexes

success = drop_mongodb_indexes(mongo_db)
if success:
    print("Indexes dropped successfully")
```

---

#### `create_neo4j_indexes(tx)`

Create indexes on Neo4j database.

**Parameters:**
- `tx` (neo4j.work.Transaction): Neo4j transaction object

**Indexes Created:**
- `idx_airport_code` on Airport.airport_code
- `idx_ct_distance_time` on CONNECTED_TO relationship properties

**Example:**
```python
from db_utils import create_neo4j_indexes

with driver.session() as session:
    session.execute_write(create_neo4j_indexes)
```

---

#### `drop_neo4j_indexes(tx)`

Drop Neo4j indexes.

**Parameters:**
- `tx` (neo4j.work.Transaction): Neo4j transaction object

**Example:**
```python
from db_utils import drop_neo4j_indexes

with driver.session() as session:
    session.execute_write(drop_neo4j_indexes)
```

---

## Module: config.py

### Constants

#### Database Configuration

```python
NEO4J_URI: str
NEO4J_USER: str
NEO4J_PASSWORD: str
MONGO_URI: str
MONGO_DB_NAME: str
```

Source: Environment variables via `.env` file

**Example:**
```python
from config import NEO4J_URI, MONGO_URI

print(f"Neo4j: {NEO4J_URI}")
print(f"MongoDB: {MONGO_URI}")
```

---

#### Application Configuration

```python
APP_TITLE: str = "Flight Ticket Sales & Performance Analysis Dashboard"
APP_ICON: str = "chart_with_upwards_trend"
PAGE_LAYOUT: str = "wide"
```

---

## Data Models

### Sales Result DataFrame

**Columns:**
| Column | Type | Description |
|--------|------|-------------|
| date | datetime64 | Date of sales |
| daily_sales | float | Total sales for the day (Rp) |
| daily_orders | int | Number of orders for the day |

---

### Route Analysis DataFrame

**Columns:**
| Column | Type | Description |
|--------|------|-------------|
| origin | str | Origin airport code |
| destination | str | Destination airport code |
| distance_km | float | Route distance in kilometers |
| flight_time_hr | float | Flight duration in hours |
| total_penjualan_rute | float | Total sales for route (Rp) |
| jumlah_order_rute | int | Number of orders for route |

---

### Insight Dictionary

**Keys:**
| Key | Type | Description |
|-----|------|-------------|
| type | str | Insight category |
| title | str | Insight headline |
| content | str | Detailed insight text |

**Example:**
```json
{
  "type": "performance",
  "title": "Performance Optimization Impact",
  "content": "Optimization improves performance by 60.5% from 2.50s to 0.98s..."
}
```

---

## Error Handling

### Common Exceptions

**ConnectionError**: Database connection failed
```python
try:
    driver, mongo_client, mongo_db = init_connections()
except ConnectionError as e:
    print(f"Connection failed: {e}")
```

**ValueError**: Invalid date range
```python
if start_date > end_date:
    raise ValueError("Start date must be before end date")
```

**KeyError**: Missing data in results
```python
try:
    sales = results['total_sales']
except KeyError:
    print("Total sales data not available")
```

---

## Performance Benchmarks

### Typical Execution Times

| Operation | Without Optimization | With Optimization | Improvement |
|-----------|---------------------|-------------------|-------------|
| Total Sales Query | 0.1s | 0.08s | 20% |
| Daily Trend | 0.5s | 0.3s | 40% |
| Routes Query (Neo4j) | 0.2s | 0.15s | 25% |
| Route Sales (100 routes) | 5.0s | 0.8s | 84% |
| **Total** | **5.8s** | **1.3s** | **78%** |

---

## Code Examples

### Complete Analysis Example

```python
from datetime import datetime
from db_utils import init_connections, create_mongodb_indexes
from analytics import (
    run_scenario_without_optimization,
    run_scenario_with_optimization,
    generate_insights
)

# Initialize connections
driver, mongo_client, mongo_db = init_connections()
orders_collection = mongo_db["orders"]

# Date range
start_date = datetime(2023, 3, 10)
end_date = datetime(2023, 4, 9)
period_days = (end_date - start_date).days + 1

# Create indexes for optimization
create_mongodb_indexes(mongo_db)

# Run scenarios
results1 = run_scenario_without_optimization(
    orders_collection, driver, start_date, end_date
)
results2 = run_scenario_with_optimization(
    orders_collection, driver, start_date, end_date
)

# Generate insights
insights = generate_insights(results1, results2, period_days)

# Display results
print("=== Performance Comparison ===")
print(f"Without Optimization: {results1['mongo_routes_time']:.2f}s")
print(f"With Optimization: {results2['mongo_routes_time']:.2f}s")
print(f"Improvement: {((results1['mongo_routes_time'] - results2['mongo_routes_time']) / results1['mongo_routes_time'] * 100):.1f}%")

print("\n=== Business Insights ===")
for insight in insights:
    print(f"\n[{insight['type'].upper()}] {insight['title']}")
    print(insight['content'])

# Cleanup
driver.close()
mongo_client.close()
```

---

For more examples and documentation, see:
- README.md
- ARCHITECTURE.md
- Individual function docstrings in source files
