# Deployment Guide

This guide covers deploying the Flight Sales Dashboard to various environments.

## Local Development Deployment

### Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/flight-sales-dashboard.git
cd flight-sales-dashboard

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run application
streamlit run app.py
```

The application will be available at `http://localhost:8501`

### Development Best Practices

- Use a separate development database
- Keep local .env file with development credentials
- Never commit sensitive credentials
- Test changes thoroughly before committing

## Streamlit Cloud Deployment

Streamlit Cloud offers the easiest deployment option.

### Prerequisites

- GitHub account
- Repository pushed to GitHub
- Working local version

### Deployment Steps

1. **Visit Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Sign in with GitHub

2. **Connect Repository**
   - Select your GitHub username
   - Select the repository: flight-sales-dashboard
   - Select branch: main
   - Set file path: app.py

3. **Configure Environment Variables**
   - Click "Advanced settings"
   - Add secrets:
     ```
     NEO4J_URI = "your_neo4j_uri"
     NEO4J_USER = "neo4j"
     NEO4J_PASSWORD = "your_password"
     MONGO_URI = "your_mongodb_uri"
     MONGO_DB_NAME = "ticketing"
     ```

4. **Deploy**
   - Click "Deploy"
   - Wait for deployment to complete
   - Your app will be available at: `https://your-username-flight-sales-dashboard.streamlit.app`

### Managing Streamlit Cloud Apps

- Update automatically when pushing to GitHub
- View logs: Click menu → "Manage app"
- Restart app: Settings → "Reboot"
- Monitor performance and usage

## Docker Deployment

Docker enables consistent deployment across different environments.

### Build Docker Image

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Configure Streamlit
RUN mkdir -p ~/.streamlit && \
    echo "[server]" > ~/.streamlit/config.toml && \
    echo "headless = true" >> ~/.streamlit/config.toml && \
    echo "port = 8501" >> ~/.streamlit/config.toml

# Run Streamlit app
CMD ["streamlit", "run", "app.py"]
```

**Build command:**
```bash
docker build -t flight-sales-dashboard:1.0.0 .
```

### Run Docker Container

```bash
# Basic run
docker run -p 8501:8501 --env-file .env flight-sales-dashboard:1.0.0

# Run with volume mount for logs
docker run -p 8501:8501 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  flight-sales-dashboard:1.0.0

# Run in background
docker run -d \
  -p 8501:8501 \
  --name flight-dashboard \
  --env-file .env \
  flight-sales-dashboard:1.0.0
```

### Docker Compose (Multi-container)

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8501:8501"
    environment:
      NEO4J_URI: ${NEO4J_URI}
      NEO4J_USER: ${NEO4J_USER}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
      MONGO_URI: ${MONGO_URI}
      MONGO_DB_NAME: ${MONGO_DB_NAME}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

**Deploy:**
```bash
docker-compose up -d
```

## AWS Deployment

### Using Elastic Beanstalk

1. **Install AWS CLI**
   ```bash
   pip install awsebcli
   ```

2. **Initialize Elastic Beanstalk**
   ```bash
   eb init -p docker flight-sales-dashboard
   ```

3. **Create Environment Variables**
   - Create `.elasticbeanstalk/env.yml`:
   ```yaml
   environments:
     prod:
       NEO4J_URI: your_value
       NEO4J_USER: your_value
       NEO4J_PASSWORD: your_value
       MONGO_URI: your_value
       MONGO_DB_NAME: your_value
   ```

4. **Deploy**
   ```bash
   eb create flight-dashboard-env
   eb deploy
   ```

### Using EC2

1. **Launch EC2 Instance**
   - Ubuntu 20.04 LTS
   - t3.medium or larger
   - Security group with port 8501 open

2. **Connect and Setup**
   ```bash
   ssh -i your-key.pem ubuntu@your-instance-ip
   
   # Install dependencies
   sudo apt-get update
   sudo apt-get install -y python3-pip git
   
   # Clone repository
   git clone https://github.com/yourusername/flight-sales-dashboard.git
   cd flight-sales-dashboard
   
   # Install Python packages
   pip3 install -r requirements.txt
   
   # Create .env file with credentials
   nano .env
   ```

3. **Run with Systemd**
   - Create `/etc/systemd/system/streamlit.service`:
   ```ini
   [Unit]
   Description=Flight Sales Dashboard
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/flight-sales-dashboard
   EnvironmentFile=/home/ubuntu/flight-sales-dashboard/.env
   ExecStart=/usr/bin/python3 -m streamlit run app.py --server.port=8501
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```
   
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable streamlit
   sudo systemctl start streamlit
   ```

## Kubernetes Deployment

For production-grade deployments.

### Kubernetes Manifests

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flight-sales-dashboard
  labels:
    app: flight-dashboard
spec:
  replicas: 2
  selector:
    matchLabels:
      app: flight-dashboard
  template:
    metadata:
      labels:
        app: flight-dashboard
    spec:
      containers:
      - name: app
        image: flight-sales-dashboard:1.0.0
        ports:
        - containerPort: 8501
        env:
        - name: NEO4J_URI
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: neo4j-uri
        - name: MONGO_URI
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: mongo-uri
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 30
          periodSeconds: 10
```

**service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: flight-dashboard-service
spec:
  selector:
    app: flight-dashboard
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8501
  type: LoadBalancer
```

**Deploy:**
```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl get service flight-dashboard-service
```

## CI/CD Pipeline Setup

### GitHub Actions

**.github/workflows/deploy.yml:**
```yaml
name: Deploy to Streamlit Cloud

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Test Code
        run: |
          pip install -r requirements.txt
          python -m pytest tests/
      
      - name: Lint Code
        run: |
          pip install pylint
          pylint *.py
      
      - name: Deploy
        run: echo "Deployment triggered to Streamlit Cloud"
```

## Post-Deployment Verification

### Health Checks

```bash
# Test application availability
curl http://localhost:8501/_stcore/health

# Test database connectivity
streamlit run test_connections.py
```

### Monitoring Setup

1. **Application Performance**
   - Monitor Streamlit server logs
   - Track response times
   - Monitor resource usage

2. **Database Health**
   - Check connection pool status
   - Monitor query execution times
   - Track error rates

3. **Infrastructure**
   - CPU and memory usage
   - Disk space availability
   - Network connectivity

## Backup and Recovery

### Database Backups

```bash
# MongoDB backup
mongodump --uri="your_mongodb_uri" --out=./backup

# Restore
mongorestore --uri="your_mongodb_uri" ./backup
```

### Code Backups

- Use GitHub with regular commits
- Tag releases: `git tag -a v1.0.0 -m "Release version 1.0.0"`
- Maintain changelog in CHANGELOG.md

## Troubleshooting Deployment Issues

### Common Issues

**Port Already in Use**
```bash
# Change port
streamlit run app.py --server.port 8502
```

**Database Connection Timeout**
- Verify connection string in .env
- Check database credentials
- Ensure firewall allows connections
- Verify network connectivity

**Missing Dependencies**
```bash
pip install --upgrade -r requirements.txt
```

**Out of Memory**
- Increase container/instance memory
- Reduce date range for analysis
- Implement caching strategy

## Rollback Procedure

### Streamlit Cloud
1. Go to app settings
2. Click "Settings" → "Repository"
3. Choose previous commit or branch

### Docker
```bash
docker run -p 8501:8501 \
  --env-file .env \
  flight-sales-dashboard:previous-version
```

### Kubernetes
```bash
kubectl rollout undo deployment/flight-sales-dashboard
kubectl rollout history deployment/flight-sales-dashboard
```

## Support and Documentation

- Check README.md for setup help
- Review ARCHITECTURE.md for system design
- Check logs for error details
- Create issues on GitHub for problems

---

For more information, see:
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Docker Documentation](https://docs.docker.com/)
- [AWS Deployment Guide](https://aws.amazon.com/getting-started/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
