# API Integration

## Overview

The API integrates with the ETL pipeline through environment variables and database connections. It provides type-safe access to the food knowledge graph with real-time capabilities.

## Environment Configuration

### Database Configuration
- `GRAPH_DB_PATH` → SQLite database path to open
- `GRAPH_BUILD_ROOT` → Where to find JSONL deliverables (`out/search_docs.jsonl`, `out/tpt_meta.jsonl`, etc.)

### Example Development Setup
```bash
# Legacy database
GRAPH_DB_PATH=etl/dist/database/graph.dev.sqlite pnpm dev

# Graph database
GRAPH_DB_PATH=etl/build/database/graph.dev.sqlite pnpm dev
```

## API Endpoints

### Search
- `search.search` - Full-text search across taxa, parts, and TPTs
- `search.suggest` - Autocomplete suggestions

### Navigation
- `navigation.getTaxon` - Get taxon details with children
- `navigation.getPart` - Get part details with children
- `navigation.getTpt` - Get TPT details

### Nutrition
- `nutrition.getNutrientProfile` - Get aggregated nutrient profile for a TPT
- `nutrition.getNutrientEvidence` - Get detailed evidence for a TPT
- `nutrition.searchNutrients` - Search for nutrients by name or ID

### Metadata
- `metadata.getFlags` - Get available flags
- `metadata.getFamilies` - Get TPT families
- `metadata.getCuisines` - Get cuisine types

## Database Integration

### Connection Management
```typescript
import { db } from "~/server/db";

// Database connection is managed automatically
const result = await db.query(`
  SELECT * FROM nutrient_profile_rollup 
  WHERE tpt_id = ?
`, [tptId]);
```

### Query Patterns
```typescript
// Search queries
const searchResults = await db.query(`
  SELECT * FROM search_docs 
  WHERE content MATCH ? 
  ORDER BY rank
`, [query]);

// Navigation queries
const taxonChildren = await db.query(`
  SELECT * FROM nodes 
  WHERE parent_id = ? 
  ORDER BY label
`, [taxonId]);

// Nutrition queries
const nutrientProfile = await db.query(`
  SELECT * FROM nutrient_profile_rollup 
  WHERE tpt_id = ?
`, [tptId]);
```

## Type Safety

### Generated Types
The API generates TypeScript types automatically:

```typescript
import { api } from './utils/api';

// Type-safe API calls
const profile: NutrientProfile = await api.nutrition.getNutrientProfile.query({
  tptId: "tpt:tx:p:malus:domestica:part:fruit:FRESH:abc123"
});
```

### Input Validation
```typescript
import { z } from "zod";

const getNutrientProfileSchema = z.object({
  tptId: z.string().min(1)
});

// Automatic validation
const result = await api.nutrition.getNutrientProfile.query({
  tptId: "valid-tpt-id"
});
```

## Performance Optimization

### Caching Strategy
- Query results cached for 5 minutes
- Search results cached for 1 minute
- Metadata cached for 1 hour
- Database connection pooling

### Query Optimization
- Prepared statements for common queries
- Index optimization for search
- Batch queries where possible
- Connection reuse

### Response Optimization
- JSON compression
- Pagination for large results
- Field selection for specific needs
- Error handling optimization

## Error Handling

### Error Types
- **Validation Errors**: Input validation failures
- **Database Errors**: SQLite operation failures
- **Not Found Errors**: Resource not found
- **Rate Limit Errors**: Too many requests

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

### Error Recovery
- Automatic retry for transient errors
- Graceful degradation for partial failures
- Detailed error logging
- User-friendly error messages

## Testing Integration

### Unit Testing
```typescript
import { api } from './utils/api';

describe('Nutrition API', () => {
  it('should get nutrient profile', async () => {
    const result = await api.nutrition.getNutrientProfile.query({
      tptId: "test-tpt-id"
    });
    
    expect(result).toBeDefined();
    expect(result.profile).toBeArray();
  });
});
```

### Integration Testing
```typescript
import { db } from "~/server/db";

describe('Database Integration', () => {
  it('should connect to database', async () => {
    const result = await db.query("SELECT 1 as test");
    expect(result[0].test).toBe(1);
  });
});
```

## Monitoring and Observability

### Logging
- Structured logging with JSON format
- Request/response logging
- Error logging with context
- Performance metrics

### Metrics
- Request count and duration
- Database query performance
- Cache hit rates
- Error rates by endpoint

### Health Checks
- Database connectivity
- Cache status
- Memory usage
- Response times

## Security Considerations

### Input Validation
- All inputs validated with Zod schemas
- SQL injection prevention
- XSS protection
- Rate limiting

### Authentication
- Currently public API
- Future JWT token support
- Role-based access control
- API key management

### Data Protection
- No sensitive data in logs
- Secure database connections
- Input sanitization
- Output encoding

## Deployment Integration

### Environment Variables
```bash
# Production
GRAPH_DB_PATH=/app/data/graph.prod.sqlite
GRAPH_BUILD_ROOT=/app/build
NODE_ENV=production

# Development
GRAPH_DB_PATH=./build/database/graph.dev.sqlite
GRAPH_BUILD_ROOT=./build
NODE_ENV=development
```

### Docker Integration
```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3001
CMD ["npm", "start"]
```

### Health Checks
```bash
# Health check endpoint
curl http://localhost:3001/api/health

# Database health
curl http://localhost:3001/api/health/db
```

## Future Enhancements

### Planned Features
- Real-time updates via WebSocket
- GraphQL compatibility
- Advanced caching strategies
- Authentication and authorization

### Performance Improvements
- Database query optimization
- Response compression
- CDN integration
- Advanced monitoring

### Developer Experience
- OpenAPI specification
- SDK generation
- Interactive documentation
- Development tools