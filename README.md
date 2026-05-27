# Coworking AI Platform

## Enterprise-Grade AI Agentic Harness for Co-Working Space Discovery

An autonomous, multi-agent AI platform that functions as an intelligent commercial real-estate procurement assistant. It helps startups, enterprises, and remote teams discover the best co-working spaces and managed offices through natural language conversations.

## Architecture Overview

```
                    [User]
                      |
                [Next.js Frontend]
                      |
              [API Gateway / Kong]
                      |
       +--------------+--------------+
       |              |              |
[Orchestrator]   [Search]      [Pricing]
       |              |              |
[AI Agents]     [PostgreSQL]   [PostgreSQL]
       |              |              |
   [OpenAI]      [Redis Cache]   [Redis Cache]
   [Claude]
```

## Microservices

| Service | Port | Description |
|---------|------|-------------|
| Gateway | 8080 | API Gateway, Auth, Rate Limiting |
| Orchestrator | 8000 | AI Agent Orchestration Engine |
| Search | 8001 | Workspace Discovery & Indexing |
| Pricing | 8002 | TCO Analysis & Pricing Intelligence |
| Frontend | 3000 | Next.js React Application |
| Postgres | 5432 | PostgreSQL + pgvector |
| Redis | 6379 | Caching & Session Store |

## AI Agent System

### Specialized Agents

1. **Requirement Understanding Agent** - Extracts structured requirements from natural language
2. **Planner Agent** - Creates execution plans and task prioritization
3. **Location Intelligence Agent** - Analyzes commute, transit, infrastructure
4. **Discovery Agent** - Searches across 10+ providers (WeWork, IndiQube, Awfis, etc.)
5. **Pricing Agent** - Calculates TCO with GST, hidden charges, deposits
6. **Optimization Agent** - Multi-objective scoring and Pareto optimization
7. **Negotiation Agent** - Strategy, discount prediction, email generation
8. **Report Agent** - Executive summaries, PDF/Excel generation
9. **Feedback Learning Agent** - Improves recommendations via RL feedback

### Execution Loop

```
Observe -> Plan -> Execute -> Evaluate -> Retry -> Optimize -> Finalize
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for frontend dev)
- Python 3.11+ (for backend dev)
- OpenAI API Key

### Local Development

```bash
# Clone and navigate
cd coworking-ai-platform

# Start infrastructure
cd infra/docker
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d

# Frontend development
cd ../../frontend
npm install
npm run dev

# Access the application
# Frontend: http://localhost:3000
# API Gateway: http://localhost:8080
# Orchestrator API: http://localhost:8000/docs
# Grafana: http://localhost:3001
```

### Kubernetes Deployment

```bash
# Using Helm
helm upgrade --install coworking-ai ./infra/helm/coworking-ai   --namespace coworking-ai   --create-namespace   --set secrets.openaiApiKey=$OPENAI_API_KEY   --set secrets.jwtSecret=$(openssl rand -base64 32)

# Using raw manifests
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/configmap.yaml
kubectl apply -f infra/k8s/secret.yaml
kubectl apply -f infra/k8s/postgres.yaml
kubectl apply -f infra/k8s/redis.yaml
kubectl apply -f infra/k8s/orchestrator.yaml
kubectl apply -f infra/k8s/gateway.yaml
kubectl apply -f infra/k8s/search.yaml
kubectl apply -f infra/k8s/pricing.yaml
kubectl apply -f infra/k8s/frontend.yaml
```

### Terraform (AWS Infrastructure)

```bash
cd infra/terraform
terraform init
terraform plan -var="environment=production"
terraform apply -var="environment=production"
```

## API Endpoints

### Orchestrator
- `POST /api/v1/orchestrator/search` - Start AI-powered search
- `GET /api/v1/orchestrator/conversations/{id}` - Get conversation history
- `POST /api/v1/orchestrator/conversations/{id}/messages` - Send message
- `GET /api/v1/orchestrator/recommendations/{id}` - Get recommendations

### Search
- `GET /api/v1/search/workspaces` - Search and filter workspaces
- `GET /api/v1/search/workspaces/{id}` - Get workspace details
- `GET /api/v1/search/providers` - List supported providers

### Pricing
- `POST /api/v1/pricing/calculate` - Calculate pricing breakdown
- `POST /api/v1/pricing/compare` - Compare multiple workspaces

## Database Schema

PostgreSQL with pgvector extension supports:
- Multi-tenant architecture
- Vector embeddings for semantic search
- Full-text search with trigram indexing
- Structured JSONB fields for flexibility

## Observability

- **Prometheus** metrics at `:9090`
- **Grafana** dashboards at `:3001`
- **OpenTelemetry** distributed tracing
- Structured logging with structlog

## Security

- JWT-based authentication
- OAuth2 / SSO ready
- Role-based access control (Admin, Manager, Member, Viewer)
- API rate limiting
- Audit logging
- TLS via cert-manager

## Supported Providers

- WeWork
- IndiQube
- Awfis
- Smartworks
- Regus
- 91Springboard
- CoWrks
- BHIVE
- Simpliwork
- TableSpace

## License

MIT License - Enterprise Commercial License available on request.
