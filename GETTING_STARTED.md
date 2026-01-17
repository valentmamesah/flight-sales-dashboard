# Flight Sales Dashboard - Getting Started Guide 

Welcome to the Flight Sales Dashboard! This guide will help you get started with the reorganized and internationalized project.

## Quick Overview

### What is This Project?
A **Streamlit-based web application** that analyzes flight ticket sales data and compares database performance between optimized and non-optimized query execution.

### Key Features
- Real-time flight ticket sales analysis
- Daily sales trend visualization
- Route performance analysis
- Database performance benchmarking
- Business insights and recommendations
- Interactive Plotly visualizations

### Technology Stack
- **Frontend:** Streamlit (interactive web framework)
- **Databases:** MongoDB (document data), Neo4j (graph data)
- **Data Processing:** Pandas, NumPy
- **Visualization:** Plotly
- **Language:** Python 3.8+

---

## New Project Structure Explained

### Folder Organization

```
flight-sales-dashboard/
├── src/                    # Source code (organized by layer)
│   ├── ui/                # User Interface layer
│   │   └── dashboard.py   # Main Streamlit application
│   └── core/              # Core business logic
│       ├── database.py    # Database operations
│       └── analytics.py   # Analytics & insights
├── config/                # Configuration
│   └── config.py          # Settings & environment variables
├── tests/                 # Testing
│   └── test_patterns.py   # Test examples and patterns
├── docs/                  # Documentation folder
├── requirements.txt       # Python dependencies
└── run.py                 # Application launcher
```

### Why This Structure?

1. **Separation of Concerns**
   - `src/ui/` - Only UI logic (Streamlit)
   - `src/core/` - Business logic, database operations, analytics
   - `config/` - Settings and environment configuration
   - `tests/` - All testing code

2. **Easy Navigation**
   - Find database operations → `src/core/database.py`
   - Find analytics functions → `src/core/analytics.py`
   - Find UI components → `src/ui/dashboard.py`
   - Find settings → `config/config.py`

3. **Scalability**
   - Easy to add new modules
   - Clear boundaries between components
   - Simple to understand for new developers

---

## Getting Started in 5 Minutes

### Step 1: Clone and Navigate
```bash
git clone https://github.com/your-username/flight-sales-dashboard.git
cd flight-sales-dashboard
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Database Credentials
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your database credentials
# Add your MongoDB URI, Neo4j credentials, etc.
nano .env  # or open with your editor
```

### Step 5: Run the Application
```bash
python run.py
# Opens at: http://localhost:8501
```

---

## How to Use the Application

### Dashboard Overview
When you run the application, you'll see **5 tabs**:

1. **Scenario 1: Without Optimization**
   - Shows query execution WITHOUT indexes
   - Individual route queries
   - Performance baseline
   - Click "Run Scenario 1" button

2. **Scenario 2: With Optimization**
   - Shows query execution WITH indexes
   - Batch processing for routes
   - Optimized performance
   - Click "Run Scenario 2" button

3. **Performance Comparison**
   - Compares execution times
   - Shows performance improvement percentage
   - Detailed breakdown by query type
   - Visual performance chart

4. **Business Insights**
   - Route efficiency analysis
   - Daily sales statistics
   - Key performance findings
   - Recommendations

5. **Data Visualization**
   - Sales trend charts
   - Route performance visualizations
   - Distribution analysis
   - Summary statistics

### Sidebar Controls

**Configuration Period**
- Select preset: "Ramadhan 2023" (March 10 - April 9, 2023)
- Or select custom dates

**Index Management**
- **Create Index:** Creates database indexes (faster queries)
- **Drop Index:** Removes indexes (slower queries for testing)

---

## Code Navigation Guide

### Finding Things

**Where is the main application?**
→ `src/ui/dashboard.py`

**Where are database functions?**
→ `src/core/database.py`
- `init_connections()` - Create database connections
- `create_mongodb_indexes()` - Create indexes
- `drop_mongodb_indexes()` - Remove indexes

**Where are analytics functions?**
→ `src/core/analytics.py`
- `get_sales_by_date()` - Calculate daily sales
- `run_scenario_without_optimization()` - Demo unoptimized queries
- `run_scenario_with_optimization()` - Demo optimized queries
- `generate_insights()` - Create business insights

**Where is configuration?**
→ `config/config.py`
- Database URIs and credentials
- Application settings
- Default values

**Where are test examples?**
→ `tests/test_patterns.py`
- Sample test cases
- Testing patterns
- Mock examples

---

## Importing Modules (For Developers)

### Correct Import Paths (New Structure)

```python
# Import from config
from config.config import APP_TITLE, MONGO_URI, NEO4J_URI

# Import database functions
from src.core.database import init_connections, create_mongodb_indexes

# Import analytics functions
from src.core.analytics import run_scenario_without_optimization, generate_insights

# Import from UI module
from src.ui.dashboard import render_sidebar_controls
```

### Creating New Modules

If you want to add new modules, follow this pattern:

```python
# src/core/new_module.py
"""
New module description
"""

def new_function():
    """Function description"""
    pass
```

Then update `src/core/__init__.py`:
```python
from .new_module import new_function
__all__ = ['new_function']
```

---

## Running Tests

### Run All Tests
```bash
pytest tests/test_patterns.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_patterns.py::TestAnalytics -v
```

### Run with Coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

---

## Documentation Guide

### For Quick Start
1. **START HERE:** This file (you're reading it!)
2. **READ:** `README.md` - Project overview and features
3. **THEN:** `QUICKSTART.md` - 5-minute setup

### For Understanding the System
1. **READ:** `ARCHITECTURE.md` - System design
2. **THEN:** `API_REFERENCE.md` - Function details
3. **FINALLY:** `src/core/` module docstrings

### For Deployment
1. **READ:** `DEPLOYMENT.md` - Deployment options
2. **CHOOSE:** Your deployment platform (Cloud, Docker, AWS, etc.)
3. **FOLLOW:** Step-by-step instructions

### For Contributing
1. **READ:** `CONTRIBUTING.md` - Contribution guidelines
2. **FOLLOW:** Code style and commit conventions
3. **SUBMIT:** Pull request

---

## Troubleshooting

### Problem: "Failed to connect to databases"
**Solution:**
1. Check `.env` file credentials
2. Verify MongoDB and Neo4j are running
3. Test connectivity: `ping your-mongodb-server`
4. Check firewall settings

### Problem: "ModuleNotFoundError"
**Solution:**
1. Ensure you're in the project root directory
2. Verify virtual environment is activated
3. Check Python path: `echo $PYTHONPATH`
4. Reinstall packages: `pip install -r requirements.txt`

### Problem: "Port 8501 already in use"
**Solution:**
```bash
# Run on different port
streamlit run src/ui/dashboard.py --server.port 8502
```

### Problem: "No data displayed"
**Solution:**
1. Ensure sample data is loaded in databases
2. Verify date range includes data
3. Check database indexes are created
4. Review database query results

### Problem: "Slow performance"
**Solution:**
1. Click "Create Index" in sidebar
2. Verify database indexes are created
3. Check database server resources
4. Run "Scenario 2" with optimization

---

## Environment Variables

### Required Variables
```
# MongoDB
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net

# Neo4j
NEO4J_URI=neo4j+s://instance.databases.neo4j.io:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# MongoDB Database Name
MONGO_DB_NAME=flight_sales
```

### Example .env File
See `.env.example` in project root for template.

---

## Useful Commands

### Development
```bash
# Activate virtual environment
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate             # Windows

# Install/update dependencies
pip install -r requirements.txt

# Run application
python run.py

# Run tests
pytest tests/test_patterns.py -v
```

### Project Organization
```bash
# View project structure
tree                              # Linux/macOS
dir /s                           # Windows

# Check file sizes
du -sh src/                       # Linux/macOS
dir /s src\                       # Windows
```

### Git
```bash
# View changes
git status
git diff

# Commit changes
git add .
git commit -m "Description"

# Push to GitHub
git push origin main
```

---

## Key File Descriptions

| File | Purpose | Size |
|------|---------|------|
| `src/ui/dashboard.py` | Main Streamlit application | 800+ lines |
| `src/core/database.py` | Database operations | 130 lines |
| `src/core/analytics.py` | Analytics functions | 350 lines |
| `config/config.py` | Configuration settings | 30 lines |
| `tests/test_patterns.py` | Test examples | 250 lines |
| `README.md` | Project documentation | 450 lines |
| `ARCHITECTURE.md` | Technical details | 600 lines |
| `run.py` | Application launcher | 15 lines |

---

## Next Steps

1. **Explore the Code**
   - Read `src/core/database.py` to understand database operations
   - Read `src/core/analytics.py` to see how queries are executed
   - Read `src/ui/dashboard.py` to understand UI logic

2. **Run the Application**
   - Execute `python run.py`
   - Test both scenarios
   - View performance comparison

3. **Study the Documentation**
   - Read `ARCHITECTURE.md` for system design
   - Read `API_REFERENCE.md` for function details
   - Check module docstrings in code

4. **Extend the Project**
   - Add new analytics functions
   - Create new visualization tabs
   - Implement additional features

5. **Push to GitHub**
   - Verify all tests pass
   - Commit your changes
   - Push to your GitHub repository

---

## Useful Resources

- **Streamlit Documentation:** https://docs.streamlit.io
- **MongoDB Drivers:** https://pymongo.readthedocs.io
- **Neo4j Python Driver:** https://neo4j.com/docs/python-manual
- **Pandas Documentation:** https://pandas.pydata.org/docs
- **Plotly Documentation:** https://plotly.com/python

---

## Support

For questions or issues:
1. Check `CONTRIBUTING.md` for guidelines
2. Review existing GitHub issues
3. Create a new issue with details
4. Read troubleshooting section above

---

## Summary

You now have a **professional, production-ready** Flight Sales Dashboard that is:
- ✓ Fully internationalized to English
- ✓ Professionally organized by functionality
- ✓ Well-documented and easy to understand
- ✓ Ready for GitHub and production deployment
- ✓ Scalable and maintainable

Happy analyzing! 📊

---

*For more detailed information, see the other documentation files:*
- `README.md` - Complete project documentation
- `QUICKSTART.md` - Quick start checklist
- `ARCHITECTURE.md` - System architecture
- `API_REFERENCE.md` - Complete API documentation
