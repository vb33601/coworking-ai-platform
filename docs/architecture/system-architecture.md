# Coworking AI Platform - System Architecture

## High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        USER[User / Browser]
        MOBILE[Mobile App]
        API_CLIENT[API Clients]
    end

    subgraph "Edge Layer"
        CDN[CloudFront / CDN]
        WAF[AWS WAF]
    end

    subgraph "Gateway Layer"
        LB[Load Balancer]
        GATEWAY[API Gateway<br/>Kong / Nginx]
        AUTH[JWT / OAuth2<br/>Auth Service]
    end

    subgraph "Service Mesh"
        ORCH[Orchestrator Service<br/>FastAPI + LangGraph]
        SEARCH[Search Service<br/>FastAPI]
        PRICE[Pricing Service<br/>FastAPI]
        NOTIFY[Notification Service<br/>FastAPI]
        ANALYT[Analytics Service<br/>FastAPI]
    end

    subgraph "AI Engine"
        REQ[Requirement Agent]
        PLAN[Planner Agent]
        LOC[Location Agent]
        DISC[Discovery Agent]
        PRIC[Pricing Agent]
        OPT[Optimization Agent]
        NEG[Negotiation Agent]
        REP[Report Agent]
        FEED[Feedback Agent]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL<br/>+ pgvector)]
        REDIS[(Redis Cache)]
        ES[(Elasticsearch)]
        S3[(S3 / Object Storage)]
    end

    subgraph "External APIs"
        OPENAI[OpenAI / Claude]
        MAPS[Google Maps / Mapbox]
        PROVIDERS[Co-working APIs]
        CAL[Calendar APIs]
        EMAIL[Email APIs]
    end

    USER --> CDN
    MOBILE --> CDN
    API_CLIENT --> WAF
    CDN --> WAF
    WAF --> LB
    LB --> GATEWAY
    GATEWAY --> AUTH
    GATEWAY --> ORCH
    GATEWAY --> SEARCH
    GATEWAY --> PRICE
    GATEWAY --> NOTIFY
    GATEWAY --> ANALYT

    ORCH --> REQ
    ORCH --> PLAN
    ORCH --> LOC
    ORCH --> DISC
    ORCH --> PRIC
    ORCH --> OPT
    ORCH --> NEG
    ORCH --> REP
    ORCH --> FEED

    REQ --> PG
    PLAN --> REDIS
    LOC --> MAPS
    DISC --> PROVIDERS
    DISC --> ES
    PRIC --> PG
    OPT --> PG
    OPT --> REDIS
    NEG --> OPENAI
    REP --> S3
    FEED --> PG

    SEARCH --> PG
    SEARCH --> ES
    PRICE --> PG
    PRICE --> REDIS
    NOTIFY --> EMAIL
    ANALYT --> PG
    ANALYT --> REDIS
```

## Data Flow

1. **User Input** -> Frontend captures natural language requirements
2. **API Gateway** -> Authenticates, rate-limits, routes to Orchestrator
3. **Orchestrator** -> Runs the agent execution graph:
   - Requirement Understanding Agent parses input
   - Planner Agent creates execution plan
   - Discovery Agent searches workspaces
   - Pricing Agent calculates TCO
   - Optimization Agent ranks recommendations
   - Report Agent generates summary
4. **Response** -> Top 10 recommendations with reasoning, costs, pros/cons
5. **Feedback Loop** -> User feedback updates preference memory

## Scoring Engine

```
Final Score = 
  0.25 * Cost Efficiency +
  0.15 * Accessibility +
  0.15 * Amenities +
  0.15 * Scalability +
  0.15 * Employee Comfort +
  0.15 * Infrastructure Reliability
```

Weights are configurable per tenant and learned from user feedback.

## Multi-Tenancy

- Tenant isolation via `tenant_id` in all tables
- Separate vector collections per tenant
- RBAC: Admin, Manager, Member, Viewer
- API quota management per tenant plan

## Deployment Architecture

### Development
```bash
docker-compose up
```

### Staging / Production (Kubernetes)
```
AWS EKS
  |- 2+ Orchestrator pods (HPA: 2-10)
  |- 2+ Gateway pods (LoadBalancer)
  |- 2+ Search pods
  |- 2+ Pricing pods
  |- RDS PostgreSQL (Multi-AZ in prod)
  |- ElastiCache Redis
  |- S3 for reports and assets
```

## Security Architecture

- JWT tokens with RS256
- OAuth2 / SSO integration
- mTLS between services (Istio optional)
- Secrets via Kubernetes Secrets / AWS Secrets Manager
- API rate limiting per tenant
- Audit logging for all actions
- Data encryption at rest (RDS) and in transit (TLS)
