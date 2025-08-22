# SolarWinds Chat Application

A FastAPI-based backend with Streamlit frontend for intelligent documentation search and chat functionality using SolarWinds APIs and vector embeddings.

## 🚀 Features

- **FastAPI Backend**: High-performance API with async support
- **Streamlit Frontend**: Interactive web interface for chat and search
- **Vector Search**: ChromaDB integration for semantic document search
- **LLM Integration**: OpenAI GPT models for intelligent responses
- **SolarWinds Integration**: Direct API connectivity for real-time data
- **Mock Data Support**: Development-friendly mock data for testing
- **Docker Support**: Containerized deployment ready

## 📋 Prerequisites

- Python 3.10+
- Docker (optional)
- OpenAI API Key
- SolarWinds API credentials (optional for mock mode)

## 🔧 Installation

### Using UV (Recommended)

```bash
# Clone the repository
git clone https://github.com/ryanflash66/solarwinds-chat.git
cd solarwinds-chat

# Install dependencies with UV
uv sync
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/ryanflash66/solarwinds-chat.git
cd solarwinds-chat

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

## ⚙️ Configuration

1. Copy the environment template:

```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:

```env
OPENAI_API_KEY=your_openai_api_key_here
SOLARWINDS_SERVER=your_solarwinds_server
SOLARWINDS_USERNAME=your_username
SOLARWINDS_PASSWORD=your_password
```

## 🚀 Quick Start

### Start Backend (FastAPI)

```bash
# Using the provided script
./start_backend.bat  # Windows
# or
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend (Streamlit)

```bash
# Using the provided script
./start_frontend.bat  # Windows
# or
streamlit run streamlit_app.py
```

### Using Docker

```bash
# Development environment
docker-compose -f docker-compose.dev.yml up

# Production environment
docker-compose up
```

## 📁 Project Structure

```
solarwinds_chat/
├── app/                    # FastAPI application
│   ├── api/               # API routes
│   ├── core/              # Core configuration
│   ├── models/            # Pydantic models
│   ├── services/          # Business logic services
│   └── utils/             # Utility functions
├── tests/                 # Test suite
├── chroma_db/            # Vector database storage
├── streamlit_app.py      # Streamlit frontend
├── docker-compose.yml    # Docker configuration
└── pyproject.toml        # Project dependencies
```

## 🔗 API Endpoints

- `GET /` - API health check
- `POST /api/v1/chat` - Chat with documents
- `GET /api/v1/health` - Health status
- `GET /api/v1/solutions` - Get SolarWinds solutions
- `GET /api/v1/metrics` - System metrics

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test category
pytest tests/unit/
pytest tests/integration/
```

## 🐳 Docker Usage

### Development

```bash
docker-compose -f docker-compose.dev.yml up
```

### Production

```bash
docker-compose up -d
```

## 📊 Monitoring

The application includes:

- Health check endpoints
- Structured logging
- Metrics collection
- Error tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:

- Create an issue on GitHub
- Check the [documentation](docs/)
- Review the [troubleshooting guide](docs/troubleshooting.md)

## 🏗️ Architecture

The application follows a clean architecture pattern:

- **API Layer**: FastAPI routes and request/response handling
- **Service Layer**: Business logic and external integrations
- **Data Layer**: Vector database and data persistence
- **Presentation Layer**: Streamlit web interface

## 🔮 Roadmap

- [ ] Authentication and authorization
- [ ] Advanced search filters
- [ ] Export chat history
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Mobile-responsive design

---

Built with ❤️ using FastAPI, Streamlit, and ChromaDB
