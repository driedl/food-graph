# Development Guide

## Getting Started

### Prerequisites
- Node.js 18+ and pnpm
- Python 3.9+
- SQLite 3
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/your-org/food-graph.git
cd food-graph

# Install dependencies
pnpm install

# Install Python dependencies
cd etl
pip install -e .
```

### Development Setup
```bash
# Start the development servers
pnpm dev

# In another terminal, run the ETL pipeline
cd etl
python -m etl.graph.cli run build
```

## Project Structure

```
food-graph/
├── apps/
│   ├── api/                 # tRPC API server
│   └── web/                 # Next.js web application
├── packages/
│   ├── api-contract/        # Shared API types
│   ├── config/              # Shared configuration
│   └── shared/              # Shared utilities
├── etl/                     # ETL pipeline
│   ├── evidence/            # Evidence mapping system
│   ├── graph/               # Graph processing stages
│   └── lib/                 # Shared ETL utilities
├── data/
│   ├── ontology/            # Ontology data files
│   └── evidence/            # Evidence data files
└── docs/                    # Documentation
```

## Development Workflow

### 1. Making Changes

#### Frontend Changes
```bash
# Make changes to apps/web/
pnpm dev

# Changes are hot-reloaded automatically
```

#### API Changes
```bash
# Make changes to apps/api/
pnpm dev

# API changes require restart
```

#### ETL Changes
```bash
# Make changes to etl/
cd etl
python -m etl.graph.cli run build

# Test specific stage
python -m etl.graph.cli run F
```

### 2. Testing

#### Unit Tests
```bash
# Run all tests
pnpm test

# Run specific test suite
pnpm test:api
pnpm test:web
```

#### ETL Tests
```bash
cd etl
python -m pytest tests/
```

#### Integration Tests
```bash
# Test full ETL pipeline
cd etl
python -m etl.graph.cli test build
```

### 3. Code Quality

#### Linting
```bash
# Lint all code
pnpm lint

# Fix linting issues
pnpm lint:fix
```

#### Type Checking
```bash
# Check TypeScript types
pnpm type-check
```

#### Formatting
```bash
# Format code
pnpm format
```

## ETL Development

### Adding New Stages

1. Create stage directory:
```bash
mkdir etl/graph/stages/stage_h
```

2. Create `__init__.py`:
```python
def run(in_dir: Path, build_dir: Path, verbose: bool = False) -> None:
    """Stage H: Your new stage"""
    # Implementation here
```

3. Create `contract.yml`:
```yaml
artifacts:
  - path: your/output/file.jsonl
    type: jsonl
    validators:
      - kind: min_rows
        min_rows: 1
```

4. Update CLI in `etl/graph/cli.py`

### Adding New Evidence Sources

1. Create source directory:
```bash
mkdir data/evidence/your-source
```

2. Add source-specific loader in `etl/evidence/lib/`

3. Update evidence mapper to include new source

4. Add source quality configuration

### Database Schema Changes

1. Update schema in `etl/graph/stages/stage_f/sqlite_pack.py`
2. Add migration logic if needed
3. Update contract validation
4. Test with existing data

## API Development

### Adding New Endpoints

1. Define procedure in `apps/api/src/server/routers/`
2. Add input/output types
3. Implement business logic
4. Add tests
5. Update API documentation

### Example Endpoint
```typescript
// apps/api/src/server/routers/nutrition.ts
export const nutritionRouter = createTRPCRouter({
  getNutrientProfile: publicProcedure
    .input(z.object({ tptId: z.string() }))
    .query(async ({ input }) => {
      // Implementation
    }),
});
```

### Database Queries

Use the shared database connection:
```typescript
import { db } from "~/server/db";

const result = await db.query(`
  SELECT * FROM nutrient_profile_rollup 
  WHERE tpt_id = ?
`, [tptId]);
```

## Frontend Development

### Adding New Pages

1. Create page in `apps/web/src/pages/`
2. Add routing if needed
3. Implement UI components
4. Add API integration
5. Add tests

### Component Development

```typescript
// apps/web/src/components/NutrientProfile.tsx
interface NutrientProfileProps {
  tptId: string;
}

export function NutrientProfile({ tptId }: NutrientProfileProps) {
  const { data, isLoading } = api.nutrition.getNutrientProfile.useQuery({
    tptId
  });

  if (isLoading) return <div>Loading...</div>;

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

## Data Management

### Adding New Foods

1. Create taxon definition in `data/ontology/taxa/`
2. Add part definitions if needed
3. Add transform definitions if needed
4. Run ETL pipeline to process
5. Test in web interface

### Adding New Evidence

1. Process external data source
2. Run evidence mapper
3. Load evidence via Stage G
4. Verify in database
5. Test API endpoints

### Ontology Updates

1. Edit JSONL files in `data/ontology/`
2. Validate changes
3. Run ETL pipeline
4. Test all functionality
5. Update documentation

## Debugging

### ETL Debugging

```bash
# Run with verbose output
python -m etl.graph.cli run build --verbose

# Run specific stage
python -m etl.graph.cli run F --verbose

# Check stage outputs
ls build/tmp/
ls build/graph/
```

### API Debugging

```bash
# Check API logs
pnpm dev:api

# Test endpoints directly
curl http://localhost:3001/api/trpc/search.search?input={"query":"apple"}
```

### Database Debugging

```bash
# Connect to database
sqlite3 build/database/graph.dev.sqlite

# Check table structure
.schema nutrient_profile_rollup

# Query data
SELECT * FROM nutrient_profile_rollup LIMIT 10;
```

## Performance Optimization

### ETL Performance

- Use batch processing for large datasets
- Optimize database queries
- Use appropriate indexes
- Monitor memory usage

### API Performance

- Implement caching strategies
- Optimize database queries
- Use connection pooling
- Monitor response times

### Frontend Performance

- Use React.memo for expensive components
- Implement virtual scrolling for large lists
- Optimize bundle size
- Use appropriate loading states

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit pull request

### Code Review

- All changes require review
- Tests must pass
- Documentation must be updated
- Performance impact considered

### Commit Messages

Use conventional commits:
```
feat: add new nutrient search endpoint
fix: resolve TPT ID generation issue
docs: update API reference
test: add unit tests for evidence mapper
```

## Troubleshooting

### Common Issues

#### ETL Pipeline Fails
- Check input data format
- Verify database permissions
- Check disk space
- Review error logs

#### API Errors
- Check database connection
- Verify endpoint parameters
- Check rate limiting
- Review server logs

#### Frontend Issues
- Check API connectivity
- Verify TypeScript types
- Check browser console
- Clear browser cache

### Getting Help

- Check existing issues on GitHub
- Review documentation
- Ask questions in discussions
- Contact maintainers

## Best Practices

### Code Quality
- Write clear, readable code
- Add comprehensive tests
- Document complex logic
- Follow existing patterns

### Performance
- Profile before optimizing
- Use appropriate data structures
- Implement caching where beneficial
- Monitor resource usage

### Security
- Validate all inputs
- Use parameterized queries
- Implement rate limiting
- Keep dependencies updated

### Documentation
- Update docs with changes
- Include code examples
- Explain complex concepts
- Keep README current
