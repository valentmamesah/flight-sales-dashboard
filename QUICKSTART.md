# Flight Ticket Sales Dashboard - Quick Start Guide

This document provides a quick reference for getting started with the Flight Sales Dashboard.

## 5-Minute Setup

### 1. Clone and Setup
```bash
git clone https://github.com/yourusername/flight-sales-dashboard.git
cd flight-sales-dashboard
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Database Credentials
```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

### 3. Run the Application
```bash
streamlit run app.py
```

Visit `http://localhost:8501` in your browser.

## What You'll See

1. **Sidebar Controls**: Select analysis period and manage database indexes
2. **5 Tabs**:
   - Scenario without optimization
   - Scenario with optimization
   - Performance comparison
   - Business insights
   - Data visualizations

## Key Features

- Compare query performance with/without optimization
- Analyze flight ticket sales trends
- Identify best-performing routes
- Generate business insights and recommendations
- Interactive data visualizations

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Failed to connect to databases" | Check .env file credentials |
| Port 8501 in use | Run on different port: `streamlit run app.py --server.port 8502` |
| No data displayed | Ensure MongoDB and Neo4j have sample data loaded |
| Slow performance | Click "Create Index" in sidebar to optimize |

## Project Files Overview

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit application |
| `config.py` | Configuration and settings |
| `db_utils.py` | Database operations |
| `analytics.py` | Analysis and insights |
| `requirements.txt` | Python dependencies |
| `.env` | Environment variables (create from .env.example) |

## Documentation

- **README.md** - Full documentation and features
- **ARCHITECTURE.md** - System design and technical details
- **DEPLOYMENT.md** - Deployment instructions
- **CONTRIBUTING.md** - Contributing guidelines

## Next Steps

1. Load sample data into MongoDB and Neo4j
2. Run both scenarios to compare performance
3. Explore the business insights
4. Customize analysis period as needed
5. Deploy to production (see DEPLOYMENT.md)

## Support

- Check existing issues on GitHub
- Review documentation files
- Create new issue if problem persists

## Learn More

- [Streamlit Docs](https://docs.streamlit.io/)
- [MongoDB Docs](https://docs.mongodb.com/)
- [Neo4j Docs](https://neo4j.com/docs/)
- [Plotly Docs](https://plotly.com/python/)
