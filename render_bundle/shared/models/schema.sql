-- ============================================================
-- Coworking AI Platform - Enterprise Database Schema
-- PostgreSQL 15+ with pgvector extension
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- TENANT & AUTH
-- ============================================================

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) DEFAULT 'starter' CHECK (plan IN ('starter','growth','enterprise')),
    settings JSONB DEFAULT '{}',
    api_quota JSONB DEFAULT '{"requests_per_minute": 60, "agents_per_month": 500}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    avatar_url TEXT,
    role VARCHAR(50) DEFAULT 'member' CHECK (role IN ('admin','manager','member','viewer')),
    department VARCHAR(100),
    preferences JSONB DEFAULT '{}',
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(255),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, email)
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),
    expires_at TIMESTAMPTZ NOT NULL,
    device_info JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AI ORCHESTRATION & MEMORY
-- ============================================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active','archived','completed')),
    requirement_schema JSONB,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user','assistant','system','tool','agent')),
    agent_name VARCHAR(100),
    tool_calls JSONB,
    tool_results JSONB,
    content TEXT,
    reasoning TEXT,
    tokens_used INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'running' CHECK (status IN ('running','completed','failed','retrying')),
    input_payload JSONB,
    output_payload JSONB,
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    tokens_used INTEGER,
    tool_calls_count INTEGER DEFAULT 0
);

CREATE TABLE memory_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL CHECK (memory_type IN ('short_term','long_term','preference','feedback','search_history','requirement')),
    category VARCHAR(100),
    key VARCHAR(255),
    value TEXT,
    embedding VECTOR(1536),
    metadata JSONB,
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 1),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memory_embedding ON memory_entries USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_memory_tenant_type ON memory_entries(tenant_id, memory_type);
CREATE INDEX idx_memory_key ON memory_entries USING gin(key gin_trgm_ops);

-- ============================================================
-- REQUIREMENTS & SEARCHES
-- ============================================================

CREATE TABLE requirement_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    raw_input TEXT,
    parsed_requirements JSONB NOT NULL,
    ambiguity_flags JSONB,
    follow_up_questions JSONB,
    confidence_score FLOAT,
    version INTEGER DEFAULT 1,
    is_finalized BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE search_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    requirement_profile_id UUID NOT NULL REFERENCES requirement_profiles(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'queued' CHECK (status IN ('queued','running','completed','failed','cancelled')),
    provider_filters JSONB,
    location_filters JSONB,
    budget_range JSONB,
    result_count INTEGER,
    execution_trace JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================================
-- WORKSPACE LISTINGS
-- ============================================================

CREATE TABLE workspace_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    website_url TEXT,
    api_base_url TEXT,
    api_key_encrypted TEXT,
    api_config JSONB,
    supported_cities JSONB,
    trust_score FLOAT DEFAULT 0.0,
    is_active BOOLEAN DEFAULT true,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES workspace_providers(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    workspace_type VARCHAR(50) CHECK (workspace_type IN ('coworking','managed_office','hot_desk','virtual_office','enterprise_suite')),
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'IN',
    postal_code VARCHAR(20),
    latitude FLOAT,
    longitude FLOAT,
    location_vector VECTOR(1536),
    amenities JSONB DEFAULT '[]',
    seating_capacity JSONB,
    pricing JSONB,
    floor_plans JSONB,
    images JSONB,
    floor VARCHAR(50),
    total_sqft INTEGER,
    parking_capacity INTEGER,
    is_24_7 BOOLEAN DEFAULT false,
    has_server_room BOOLEAN DEFAULT false,
    has_cafeteria BOOLEAN DEFAULT false,
    has_recreation BOOLEAN DEFAULT false,
    is_furnished BOOLEAN DEFAULT true,
    accessibility_features JSONB,
    security_features JSONB,
    compliance_certifications JSONB,
    sustainability_score FLOAT,
    internet_redundancy JSONB,
    contract_terms JSONB,
    availability_status VARCHAR(50) DEFAULT 'available',
    embedding VECTOR(1536),
    metadata JSONB,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider_id, external_id)
);

CREATE INDEX idx_workspace_location ON workspaces USING gist(
    ll_to_earth(latitude, longitude)
);
CREATE INDEX idx_workspace_embedding ON workspaces USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_workspace_city ON workspaces(city);
CREATE INDEX idx_workspace_type ON workspaces(workspace_type);
CREATE INDEX idx_workspace_amenities ON workspaces USING gin(amenities);
CREATE INDEX idx_workspace_pricing ON workspaces USING gin(pricing);
CREATE INDEX idx_workspace_provider ON workspaces(provider_id);

CREATE TABLE workspace_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    source VARCHAR(100),
    rating FLOAT CHECK (rating BETWEEN 0 AND 5),
    review_text TEXT,
    reviewer_info JSONB,
    sentiment_score FLOAT,
    topics JSONB,
    verified BOOLEAN DEFAULT false,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- RECOMMENDATIONS
-- ============================================================

CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    search_job_id UUID NOT NULL REFERENCES search_jobs(id) ON DELETE CASCADE,
    requirement_profile_id UUID NOT NULL REFERENCES requirement_profiles(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    overall_score FLOAT NOT NULL,
    scores JSONB NOT NULL,
    reasoning TEXT,
    pros JSONB,
    cons JSONB,
    cost_breakdown JSONB,
    commute_analysis JSONB,
    parking_analysis JSONB,
    scalability_analysis JSONB,
    risk_analysis JSONB,
    negotiation_points JSONB,
    is_favorited BOOLEAN DEFAULT false,
    user_feedback VARCHAR(50),
    feedback_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recommendations_search ON recommendations(search_job_id, rank);
CREATE INDEX idx_recommendations_workspace ON recommendations(workspace_id);

-- ============================================================
-- NEGOTIATION & REPORTS
-- ============================================================

CREATE TABLE negotiations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    recommendation_id UUID NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy JSONB,
    simulated_discount FLOAT,
    suggested_email TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    search_job_id UUID NOT NULL REFERENCES search_jobs(id) ON DELETE CASCADE,
    title VARCHAR(255),
    format VARCHAR(50) CHECK (format IN ('pdf','excel','html','json')),
    content_url TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TOOL REGISTRY & EXECUTION
-- ============================================================

CREATE TABLE tool_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100),
    input_schema JSONB NOT NULL,
    output_schema JSONB,
    provider VARCHAR(100),
    endpoint_url TEXT,
    auth_config JSONB,
    rate_limit JSONB,
    is_active BOOLEAN DEFAULT true,
    confidence_threshold FLOAT DEFAULT 0.7,
    fallback_tools JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    tool_name VARCHAR(100) NOT NULL,
    input_payload JSONB,
    output_payload JSONB,
    status VARCHAR(50) DEFAULT 'running',
    error TEXT,
    latency_ms INTEGER,
    retry_count INTEGER DEFAULT 0,
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================================
-- ANALYTICS
-- ============================================================

CREATE TABLE search_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    search_job_id UUID,
    user_id UUID,
    event_type VARCHAR(100),
    event_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_name VARCHAR(100),
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    runs_count INTEGER,
    success_rate FLOAT,
    avg_latency_ms FLOAT,
    avg_tokens_used FLOAT,
    tool_success_rates JSONB,
    error_breakdown JSONB
);

-- ============================================================
-- RAG DOCUMENTS
-- ============================================================

CREATE TABLE rag_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title VARCHAR(255),
    source_url TEXT,
    doc_type VARCHAR(50) CHECK (doc_type IN ('lease_agreement','pricing_sheet','brochure','policy','contract','floor_plan')),
    content TEXT,
    chunks JSONB,
    embedding VECTOR(1536),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rag_embedding ON rag_documents USING ivfflat (embedding vector_cosine_ops);

-- ============================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tenants_updated_at BEFORE UPDATE ON tenants FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER requirement_profiles_updated_at BEFORE UPDATE ON requirement_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER workspaces_updated_at BEFORE UPDATE ON workspaces FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER recommendations_updated_at BEFORE UPDATE ON recommendations FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER memory_entries_updated_at BEFORE UPDATE ON memory_entries FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- SEED DATA
-- ============================================================

INSERT INTO workspace_providers (name, slug, website_url, supported_cities, trust_score) VALUES
('WeWork', 'wework', 'https://www.wework.com', '["Bangalore","Mumbai","Delhi","Hyderabad","Pune"]', 4.2),
('IndiQube', 'indiqube', 'https://www.indiqube.com', '["Bangalore","Chennai","Hyderabad","Pune","Kochi"]', 4.5),
('Awfis', 'awfis', 'https://www.awfis.com', '["Bangalore","Mumbai","Delhi","Kolkata","Pune","Chennai","Hyderabad"]', 4.0),
('Smartworks', 'smartworks', 'https://www.smartworks.in', '["Bangalore","Mumbai","Delhi","Noida","Gurgaon","Pune","Hyderabad"]', 4.3),
('Regus', 'regus', 'https://www.regus.com', '["Bangalore","Mumbai","Delhi","Chennai","Hyderabad","Pune","Kolkata"]', 4.1),
('91Springboard', '91springboard', 'https://www.91springboard.com', '["Bangalore","Mumbai","Delhi","Hyderabad","Pune"]', 4.0),
('CoWrks', 'cowrks', 'https://www.cowrks.com', '["Bangalore","Mumbai","Delhi","Chennai","Hyderabad"]', 4.4),
('BHIVE', 'bhive', 'https://www.bhiveworkspace.com', '["Bangalore"]', 4.2),
('Simpliwork', 'simpliwork', 'https://www.simpliwork.com', '["Bangalore","Mumbai","Delhi","Pune","Hyderabad"]', 4.3),
('TableSpace', 'tablespace', 'https://www.tablespace.io', '["Bangalore","Mumbai","Delhi","Pune","Chennai"]', 4.1);
