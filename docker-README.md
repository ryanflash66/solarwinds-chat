# 🐳 Docker Deployment Guide

## Quick Start

### Production Deployment
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access services
# - API: http://localhost:8000
# - Frontend: http://localhost:8501  
# - ChromaDB: http://localhost:8001
```

### Development Mode
```bash
# Start with development overrides (live reloading)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Rebuild after code changes
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## Services

### 🔧 **API Service** (Port 8000)
- FastAPI backend with all chatbot functionality
- Health check: `GET /api/v1/health`
- API docs: `GET /docs` (in debug mode)

### 🎨 **Frontend Service** (Port 8501) 
- Streamlit web interface
- Connects to API service automatically
- Health check: `GET /_stcore/health`

### 🗄️ **ChromaDB Service** (Port 8001)
- Vector database for semantic search
- Persistent storage with Docker volumes
- Health check: `GET /api/v1/heartbeat`

### 🚀 **Redis Service** (Port 6379)
- Caching and background job state
- Configured with memory limits and persistence
- Health check: `redis-cli ping`

## Configuration

### Environment Variables

Set these in a `.env` file or pass via docker-compose:

```env
# LLM Configuration (required for AI responses)
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free

# SolarWinds API (optional - uses mock data if not configured)
SOLARWINDS_API_KEY=your_solarwinds_key
SOLARWINDS_BASE_URL=https://your-instance.com/api

# Development Settings
DEBUG=false
LOG_LEVEL=INFO
ENABLE_MOCK_DATA=true
```

### Volumes

- `chroma-data`: ChromaDB vector database storage
- `redis-data`: Redis persistence
- `./chroma_db`: Local ChromaDB files (bind mount)
- `./logs`: Application logs (bind mount)

## Management Commands

### Service Control
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v

# Restart specific service
docker-compose restart api

# View service status
docker-compose ps
```

### Logs and Debugging
```bash
# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api

# Execute shell in running container
docker-compose exec api bash
docker-compose exec frontend bash
```

### Database Operations
```bash
# Trigger data sync manually
curl -X POST http://localhost:8000/api/v1/sync/trigger

# Check vector database stats
curl http://localhost:8000/api/v1/solutions/stats

# Reset ChromaDB (⚠️ deletes all indexed data)
docker-compose exec chromadb curl -X POST http://localhost:8000/api/v1/reset
```

## Health Monitoring

All services include health checks accessible via:

```bash
# API service health
curl http://localhost:8000/api/v1/health

# Check all container health
docker-compose ps
```

## Troubleshooting

### Common Issues

1. **Services won't start**: Check Docker daemon is running
2. **Port conflicts**: Ensure ports 8000, 8501, 8001, 6379 are available
3. **Memory issues**: Increase Docker memory limit (recommended: 4GB+)
4. **Slow responses**: ChromaDB needs time to download models on first run

### Performance Tuning

1. **Production**: Set `DEBUG=false` and `LOG_LEVEL=INFO`
2. **Memory**: Adjust Redis `maxmemory` setting in docker-compose.yml
3. **CPU**: Scale services with `docker-compose up --scale api=2`

### Data Backup

```bash
# Backup ChromaDB
docker run --rm -v solarwinds_chroma-data:/data -v $(pwd):/backup alpine tar czf /backup/chroma-backup.tar.gz /data

# Backup Redis
docker exec solarwinds-redis redis-cli BGSAVE
docker cp solarwinds-redis:/data/dump.rdb ./redis-backup.rdb
```

## Production Checklist

- [ ] Set secure environment variables
- [ ] Configure proper logging levels
- [ ] Set up monitoring and alerts
- [ ] Configure backup strategies
- [ ] Set resource limits (CPU/memory)
- [ ] Configure reverse proxy (nginx/traefik)
- [ ] Enable HTTPS/SSL
- [ ] Set up log rotation

## Security Notes

- All services run as non-root users
- Sensitive data in environment variables only
- Network isolation via Docker networks
- No unnecessary port exposures
- Regular security updates via base image updates