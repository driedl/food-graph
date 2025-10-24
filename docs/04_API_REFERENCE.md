# API Reference

## Overview

The Food Graph API provides type-safe access to the food knowledge graph through tRPC endpoints. The API supports search, navigation, nutrition queries, and metadata access.

## Base URL

```
http://localhost:3001/api/trpc
```

## Authentication

Currently, all endpoints are public. Authentication will be added in future versions.

## Core Endpoints

### Search

#### `search.search`
Full-text search across taxa, parts, and TPTs.

**Input**:
```typescript
{
  query: string;
  limit?: number;
  offset?: number;
  filters?: {
    type?: 'taxon' | 'part' | 'tpt';
    kingdom?: 'p' | 'a' | 'f';
    category?: string;
  };
}
```

**Output**:
```typescript
{
  results: Array<{
    id: string;
    type: 'taxon' | 'part' | 'tpt';
    label: string;
    description?: string;
    metadata?: Record<string, any>;
  }>;
  total: number;
  limit: number;
  offset: number;
}
```

**Example**:
```typescript
const results = await api.search.search.query({
  query: "apple",
  limit: 10,
  filters: { type: "tpt" }
});
```

### Navigation

#### `navigation.getTaxon`
Get taxon details with children.

**Input**:
```typescript
{
  taxonId: string;
  includeChildren?: boolean;
}
```

**Output**:
```typescript
{
  id: string;
  label: string;
  description?: string;
  kingdom: 'p' | 'a' | 'f';
  parent?: string;
  children?: Array<{
    id: string;
    label: string;
    childCount: number;
  }>;
  ncbiTaxid?: number;
  lineage?: string[];
}
```

#### `navigation.getPart`
Get part details with children.

**Input**:
```typescript
{
  partId: string;
  includeChildren?: boolean;
}
```

**Output**:
```typescript
{
  id: string;
  label: string;
  description?: string;
  category: string;
  parent?: string;
  children?: Array<{
    id: string;
    label: string;
  }>;
}
```

### Nutrition

#### `nutrition.getNutrientProfile`
Get aggregated nutrient profile for a TPT.

**Input**:
```typescript
{
  tptId: string;
}
```

**Output**:
```typescript
{
  tptId: string;
  profile: Array<{
    nutrientId: string;
    nutrientName: string;
    value: number;
    unit: string;
    sourceCount: number;
    minValue: number;
    maxValue: number;
    confidence: number;
  }>;
}
```

#### `nutrition.getNutrientEvidence`
Get detailed evidence for a TPT.

**Input**:
```typescript
{
  tptId: string;
  limit?: number;
  offset?: number;
}
```

**Output**:
```typescript
{
  tptId: string;
  evidence: Array<{
    foodId: string;
    source: string;
    nutrientId: string;
    nutrientName: string;
    amount: number;
    unit: string;
    originalAmount: number;
    originalUnit: string;
    confidence: number;
    notes?: string;
  }>;
  total: number;
}
```

#### `nutrition.searchNutrients`
Search for nutrients by name or ID.

**Input**:
```typescript
{
  query: string;
  limit?: number;
}
```

**Output**:
```typescript
{
  nutrients: Array<{
    id: string;
    name: string;
    unit: string;
    class: string;
    description?: string;
  }>;
}
```

### TPT (Transformed Products)

#### `tpt.getTpt`
Get TPT details.

**Input**:
```typescript
{
  tptId: string;
}
```

**Output**:
```typescript
{
  id: string;
  taxonId: string;
  partId: string;
  transforms: Array<{
    id: string;
    params: Record<string, any>;
  }>;
  family: string;
  identityHash: string;
  metadata: {
    flags: string[];
    cuisine: string[];
    safety: string[];
  };
}
```

#### `tpt.searchTpts`
Search for TPTs by criteria.

**Input**:
```typescript
{
  query?: string;
  taxonId?: string;
  partId?: string;
  family?: string;
  flags?: string[];
  limit?: number;
  offset?: number;
}
```

**Output**:
```typescript
{
  tpts: Array<{
    id: string;
    label: string;
    taxonId: string;
    partId: string;
    family: string;
    metadata: Record<string, any>;
  }>;
  total: number;
}
```

### Metadata

#### `metadata.getFlags`
Get available flags and their descriptions.

**Output**:
```typescript
{
  flags: Array<{
    id: string;
    label: string;
    description: string;
    category: string;
  }>;
}
```

#### `metadata.getFamilies`
Get available TPT families.

**Output**:
```typescript
{
  families: Array<{
    id: string;
    label: string;
    description: string;
    color: string;
    icon: string;
  }>;
}
```

#### `metadata.getCuisines`
Get available cuisine types.

**Output**:
```typescript
{
  cuisines: Array<{
    id: string;
    label: string;
    description: string;
  }>;
}
```

## Error Handling

### Error Response Format
```typescript
{
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}
```

### Common Error Codes
- `VALIDATION_ERROR`: Input validation failed
- `NOT_FOUND`: Resource not found
- `INTERNAL_ERROR`: Server error
- `RATE_LIMITED`: Too many requests

### Example Error Handling
```typescript
try {
  const result = await api.nutrition.getNutrientProfile.query({
    tptId: "invalid-id"
  });
} catch (error) {
  if (error.data?.code === 'NOT_FOUND') {
    console.log('TPT not found');
  }
}
```

## TypeScript Integration

### Generated Types
The API generates TypeScript types automatically:

```typescript
import { api } from './utils/api';

// Type-safe API calls
const profile: NutrientProfile = await api.nutrition.getNutrientProfile.query({
  tptId: "tpt:tx:p:malus:domestica:part:fruit:FRESH:abc123"
});
```

### React Integration
```typescript
import { useQuery } from '@tanstack/react-query';

function NutrientProfile({ tptId }: { tptId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['nutrientProfile', tptId],
    queryFn: () => api.nutrition.getNutrientProfile.query({ tptId })
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {data?.profile.map(nutrient => (
        <div key={nutrient.nutrientId}>
          {nutrient.nutrientName}: {nutrient.value} {nutrient.unit}
        </div>
      ))}
    </div>
  );
}
```

## Performance

### Caching
- Query results are cached for 5 minutes
- Search results are cached for 1 minute
- Metadata is cached for 1 hour

### Rate Limiting
- 100 requests per minute per IP
- 1000 requests per hour per IP
- Burst allowance: 20 requests per second

### Response Times
- Search queries: <100ms
- Navigation queries: <50ms
- Nutrition queries: <200ms
- Metadata queries: <50ms

## Examples

### Search for Foods
```typescript
// Search for apple-related foods
const results = await api.search.search.query({
  query: "apple",
  limit: 20,
  filters: { type: "tpt" }
});

// Search for specific part
const partResults = await api.search.search.query({
  query: "fillet",
  filters: { type: "part" }
});
```

### Get Nutrition Data
```typescript
// Get nutrient profile for smoked salmon
const profile = await api.nutrition.getNutrientProfile.query({
  tptId: "tpt:tx:a:salmo:salar:part:fillet:SMOKED:abc123"
});

// Get detailed evidence
const evidence = await api.nutrition.getNutrientEvidence.query({
  tptId: "tpt:tx:a:salmo:salar:part:fillet:SMOKED:abc123",
  limit: 50
});
```

### Navigate Taxonomy
```typescript
// Get plant kingdom
const plants = await api.navigation.getTaxon.query({
  taxonId: "tx:p",
  includeChildren: true
});

// Get apple species
const apple = await api.navigation.getTaxon.query({
  taxonId: "tx:p:malus:domestica"
});
```

## Future Enhancements

### Planned Features
- Real-time updates via WebSocket
- Batch query support
- Advanced filtering options
- GraphQL compatibility
- OpenAPI specification

### Performance Improvements
- Response compression
- Advanced caching strategies
- Database query optimization
- CDN integration
