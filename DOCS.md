# 📚 Documentation Guide

**👈 START HERE!** Quick navigation to all documentation files:

## 🚀 Getting Started (Start Here!)
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Complete getting started guide with project overview, setup instructions, and navigation tips

## 📖 Main Documentation
- **[README.md](README.md)** - Project overview, features, installation, and usage
- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute quick start setup guide

## 🏗️ Technical Documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture, components, and technical design
- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete API documentation and function reference

## 📦 Deployment & Development
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment options (Streamlit Cloud, Docker, AWS, Kubernetes)
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines and development setup

## 📋 Project Information
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and feature changes
- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Project completion status and readiness
- **[COMPLETION_SUMMARY.md](COMPLETION_SUMMARY.md)** - What was accomplished summary
- **[FILE_STRUCTURE.md](FILE_STRUCTURE.md)** - Complete file and folder organization

## 📄 Legal
- **[LICENSE](LICENSE)** - MIT License

---

## Quick Command Reference

### Setup
```bash
cp .env.example .env      # Create environment file
pip install -r requirements.txt
```

### Run Application
```bash
python run.py
# or
streamlit run src/ui/dashboard.py
```

### Run Tests
```bash
pytest tests/test_patterns.py -v
```

---

## Recommended Reading Order

1. **For Quick Start (5 minutes)**
   - GETTING_STARTED.md
   - QUICKSTART.md

2. **For Understanding the Project (20 minutes)**
   - README.md
   - ARCHITECTURE.md

3. **For Development (30 minutes)**
   - CONTRIBUTING.md
   - API_REFERENCE.md
   - FILE_STRUCTURE.md

4. **For Deployment (varies)**
   - DEPLOYMENT.md

---

## Project Structure

```
flight-sales-dashboard/
├── src/                   # Source code
│   ├── ui/dashboard.py   # Main Streamlit app
│   └── core/
│       ├── database.py   # Database operations
│       └── analytics.py  # Analytics functions
├── config/config.py      # Configuration
├── tests/test_patterns.py # Test examples
├── run.py               # Application launcher
└── [documentation files]
```

---

**Status:** Production Ready | **Language:** 100% English | **License:** MIT
