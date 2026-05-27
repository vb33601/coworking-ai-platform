# API Contracts

## Orchestrator Service (Port 8000)

### POST /api/v1/orchestrator/search
Start a new AI-powered workspace search.

**Request:**
```json
{
  "tenant_id": "tenant-123",
  "user_id": "user-456",
  "raw_input": "We are a fintech startup with 80 employees looking for a managed office in Bangalore near ORR...",
  "conversation_id": "optional-existing-id"
}
```

**Response:**
```json
{
  "search_job_id": "job-789",
  "status": "completed",
  "recommendations": [
    {
      "workspace_id": "ws-001",
      "rank": 1,
      "overall_score": 92.5,
      "scores": {
        "cost_efficiency": 88,
        "accessibility": 95,
        "amenities": 90,
        "scalability": 85,
        "employee_comfort": 92,
        "infrastructure": 94
      },
      "reasoning": "Best match due to proximity to ORR, 24/7 access, and strong internet redundancy. Price is within budget with room for negotiation.",
      "pros": ["24/7 access", "Server room available", "200+ seat capacity"],
      "cons": ["Slightly higher parking cost", "3-month lock-in period"],
      "cost_breakdown": {
        "monthly_total_inr": 420000,
        "per_seat_inr": 5250,
        "tco_12_month_inr": 5250000
      }
    }
  ],
  "summary": "Top recommendation: WeWork Galaxy in Koramangala with score 92.5/100",
  "total_cost_estimate": 420000,
  "ambiguity_flags": []
}
```

## Search Service (Port 8001)

### GET /api/v1/search/workspaces
Query workspaces with filters.

**Query Parameters:**
- `city` - Filter by city
- `area` - Filter by area/neighborhood
- `workspace_type` - coworking, managed_office, hot_desk, enterprise_suite
- `min_seats` - Minimum available seats
- `max_budget_inr` - Maximum price per seat
- `providers` - List of provider slugs
- `amenities` - Required amenities
- `is_24_7` - 24/7 access required
- `meeting_rooms_min` - Minimum meeting rooms
- `parking_min` - Minimum parking capacity
- `q` - Full-text search query

**Response:**
```json
{
  "results": [...],
  "total": 42,
  "limit": 20,
  "offset": 0,
  "filters_applied": {...}
}
```

## Pricing Service (Port 8002)

### POST /api/v1/pricing/calculate
Calculate detailed pricing for a workspace configuration.

**Request:**
```json
{
  "workspace_id": "ws-001",
  "team_size": 80,
  "duration_months": 18,
  "amenities": ["server_room", "branding"],
  "parking_count": 15,
  "cabins": 2,
  "meeting_rooms": 4,
  "require_24_7": true
}
```

**Response:**
```json
{
  "workspace_id": "ws-001",
  "provider": "wework",
  "breakdown": {
    "base_seat_cost_inr": 12000,
    "seat_count": 80,
    "subtotal_inr": 1104000,
    "maintenance_inr": 88320,
    "parking_inr": 37500,
    "internet_inr": 40000,
    "gst_18_pct_inr": 222033,
    "setup_fee_inr": 80000,
    "security_deposit_inr": 2208000,
    "total_monthly_inr": 1491853,
    "per_seat_effective_inr": 18648,
    "tco_12_month_inr": 20110236
  },
  "negotiation_leverage": [
    "Bulk seat discount potential: 10%",
    "Long-term commitment discount: 10%",
    "Quick move-in discount: 3-5%"
  ]
}
```
