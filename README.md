# Flight Ticket Sales & Performance Analysis Dashboard

A application for analyzing flight ticket sales with database performance optimization comparison.

## Overview

This dashboard provides real-time analysis of flight ticket sales with a focus on understanding both business metrics and database performance optimization impacts. It compares two scenarios:

1. **Without Optimization**: Queries without proper indexing and using individual route queries
2. **With Optimization**: Queries with proper indexing and batch processing for improved performance

## Features

- Real-time flight ticket sales analysis
- Daily sales trend visualization
- Route performance analysis with distance correlation
- Database performance benchmarking
- Business insights and recommendations
- Interactive data visualization with Plotly
- Advanced analytics including route efficiency metrics

## Technology Stack

- **Frontend**: Streamlit (interactive web framework)
- **Databases**: 
  - MongoDB (orders and flight pricing data)
  - Neo4j (airport network and route graph database)
- **Data Processing**: Pandas
- **Visualization**: Plotly
- **Language**: Python 3.8+

## Prerequisites

- Python 3.8 or higher
- MongoDB Atlas account with active cluster
- Neo4j AuraDB account with active database
- Internet connection (for cloud database access)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/flight-sales-dashboard.git
cd flight-sales-dashboard
```

### 2. Create Virtual Environment

```bash
# Using venv
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your database credentials
# Update the following:
# - NEO4J_URI
# - NEO4J_USER
# - NEO4J_PASSWORD
# - MONGO_URI
# - MONGO_DB_NAME
```

### 5. Run the Application

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

## Project Structure

```
flight-sales-dashboard/
├── app.py                 # Main Streamlit application
├── config.py             # Configuration and environment variables
├── db_utils.py           # Database connection and index management
├── analytics.py          # Analysis queries and insights generation
├── requirements.txt      # Python dependencies
├── .env.example          # Example environment variables
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## File Descriptions

### app.py
Main application entry point containing:
- Page configuration
- Sidebar controls for date selection and index management
- Five main tabs for different analysis views
- Tab 1: Scenario without optimization
- Tab 2: Scenario with optimization
- Tab 3: Performance comparison
- Tab 4: Business insights
- Tab 5: Data visualization

### config.py
Configuration module handling:
- Database connection credentials
- Application settings
- Environment variable loading with sensible defaults

### db_utils.py
Database utilities providing:
- Connection initialization for MongoDB and Neo4j
- Index creation for query optimization
- Index deletion for testing scenarios
- Error handling and status reporting

### analytics.py
Analytics engine containing:
- `get_sales_by_date()`: Daily sales calculation
- `run_scenario_without_optimization()`: Queries without optimization
- `run_scenario_with_optimization()`: Queries with optimization and batch processing
- `generate_insights()`: Business intelligence and insights generation

## Usage Guide

### Starting the Dashboard

1. Ensure MongoDB and Neo4j are properly configured with data
2. Run `streamlit run app.py`
3. The dashboard loads with the default Ramadhan 2023 period (March 10 - April 9, 2023)

### Selecting Analysis Period

**Sidebar Options:**
- Use the preset "Ramadhan 2023" for quick analysis
- Select "Custom" to choose your own date range
- The system displays the analysis period duration

### Managing Database Indexes

**Index Creation:**
1. Click "Create Index" button in the sidebar
2. Wait for confirmation message
3. Indexes are created on both MongoDB and Neo4j

**Index Deletion:**
1. Click "Drop Index" button in the sidebar
2. Wait for confirmation message
3. Useful for running the non-optimized scenario

### Tab 1: Without Optimization

This scenario runs queries without proper indexing:
- Click "Run Scenario 1" to execute analysis
- View execution times for each query type
- See total sales, orders, and average order value
- Analyze top 10 best-selling routes

### Tab 2: With Optimization

This scenario runs the same queries with optimization:
- Click "Run Scenario 2" to execute optimized analysis
- Compare metrics with the non-optimized scenario
- Notice the significant performance improvement
- Uses batch processing for route analysis

### Tab 3: Performance Comparison

Detailed comparison between scenarios:
- Execution time metrics for each query type
- Performance improvement percentages
- Speedup factors
- Visualization of performance gains
- Key insights about optimization benefits

### Tab 4: Business Insights

Advanced business analytics:
- Overall sales performance summary
- Daily trend analysis (highest/lowest sales days)
- Route performance analysis
- Distance vs sales correlation analysis
- Route efficiency metrics (revenue per km, revenue per hour)
- Business recommendations

### Tab 5: Data Visualization

Interactive charts and visualizations:
- Daily sales trend line chart
- Daily sales vs orders comparison
- Top 10 routes bar chart
- Distance vs sales scatter plot
- Sales revenue distribution histogram
- Route distance distribution histogram
- Summary statistics table

## Database Schema Overview

### MongoDB (ticketing database)

**Collections:**
- `orders`: Flight ticket orders with fields like depart_date, origin, destination, total_price
- `flight_prices`: Flight pricing information

### Neo4j

**Nodes:**
- `Airport`: Represents airports with airport_code property

**Relationships:**
- `CONNECTED_TO`: Routes between airports with distance_km and flight_time_hr properties

## Query Optimization Details

### Without Optimization
- Queries without indexes (N/A index management)
- Individual queries for each route (N separate database calls)
- No filtering on Neo4j query results
- Expected execution time: Baseline (typically 5-10 seconds)

### With Optimization
- Composite indexes on commonly queried fields
- Batch processing for route queries (1 aggregation pipeline)
- Filter predicates in Neo4j query (distance > 1000 km)
- Expected execution time: 50-80% faster than baseline

### Key Improvements
1. **Index Strategy**: Creates compound indexes on date, route, and flight ID
2. **Query Batching**: Converts N individual queries to single batch query
3. **Predicate Pushdown**: Filters applied at database level, not application level
4. **Aggregation Pipeline**: Uses MongoDB aggregation framework efficiently

## Performance Metrics

The dashboard tracks the following timing metrics:

- **MongoDB Total Sales Query**: Time to calculate aggregate sales
- **Daily Trend Query**: Time to compute daily sales aggregation
- **Neo4j Routes Query**: Time to fetch route information
- **MongoDB Routes Query**: Time to calculate sales per route
- **Total Execution Time**: Combined time for all operations

Typical performance improvements with optimization:
- Individual route queries: 50-70% faster with batching
- Overall dashboard: 40-60% faster with indexes

## Troubleshooting

### Connection Issues

**Error: "Failed to connect to databases"**
- Verify MongoDB URI in .env is correct
- Verify Neo4j URI and credentials
- Check internet connection and firewall rules
- Ensure database clusters are running and accessible

### Slow Performance

**Queries taking longer than expected:**
- Create indexes using the "Create Index" button
- Check network latency to database servers
- Verify data volume is not extremely large
- Consider narrowing the date range

### Missing Data

**No results in analysis:**
- Verify data exists in both MongoDB and Neo4j
- Check that date range contains actual data
- Confirm collections and Neo4j nodes are properly named

### Streamlit Issues

**Port already in use:**
```bash
streamlit run app.py --server.port 8502
```

**Clear Streamlit cache:**
```bash
streamlit cache clear
```

## Deployment

### Local Deployment
Already covered in Installation section above.

### Cloud Deployment (Streamlit Cloud)

1. Push repository to GitHub
2. Visit https://share.streamlit.io
3. Connect your GitHub account
4. Select repository: flight-sales-dashboard
5. Set environment variables in deployment settings:
   - NEO4J_URI
   - NEO4J_USER
   - NEO4J_PASSWORD
   - MONGO_URI
   - MONGO_DB_NAME

### Docker Deployment

Create a Dockerfile:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
```

Build and run:

```bash
docker build -t flight-sales-dashboard .
docker run -p 8501:8501 --env-file .env flight-sales-dashboard
```

## Development

### Adding New Features

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes following the existing code structure
3. Test thoroughly with various date ranges
4. Commit with clear messages: `git commit -m "Add feature description"`
5. Push to branch: `git push origin feature/your-feature`
6. Create Pull Request

### Code Style

- Follow PEP 8 conventions
- Use type hints where applicable
- Write docstrings for functions and modules
- Keep functions focused and small

### Testing

Currently, manual testing through the Streamlit interface is recommended. Consider adding:
- Unit tests for analytics functions
- Integration tests for database connections
- Performance benchmarks

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure code quality and tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Contact

For questions, issues, or suggestions:
- Open an issue on GitHub
- Contact the development team

## Acknowledgments

- Streamlit for the excellent web framework
- MongoDB and Neo4j for robust database solutions
- Plotly for beautiful interactive visualizations

## References

- [Streamlit Documentation](https://docs.streamlit.io/)
- [MongoDB Aggregation Pipeline](https://docs.mongodb.com/manual/reference/operator/aggregation/)
- [Neo4j Cypher Query Language](https://neo4j.com/docs/cypher-manual/)
- [Plotly Python Graphing Library](https://plotly.com/python/)

---

**Last Updated**: January 2026
**Version**: 1.0.0
