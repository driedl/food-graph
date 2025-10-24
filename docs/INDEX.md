# Food Graph Documentation Index

_Last updated: 2025-01-27_

Welcome to the Food Graph documentation. This index provides a structured guide to understanding and working with the food knowledge graph system.

## 🚀 Getting Started

### Core Concepts
1. **[Vision & Principles](./00_VISION.md)** — Project vision, goals, and design principles
2. **[Architecture Overview](./01_ARCHITECTURE.md)** — Core entities, relationships, and system design
3. **[Evidence System](./02_EVIDENCE_SYSTEM.md)** — 3-tier evidence mapping and nutrition data integration
4. **[ETL Pipeline](./03_ETL_PIPELINE.md)** — Data processing stages and build system

## 📚 Technical Documentation

### System Components
5. **[API Reference](./04_API_REFERENCE.md)** — tRPC endpoints, queries, and usage examples
6. **[Development Guide](./05_DEVELOPMENT_GUIDE.md)** — How to contribute, build, and test
7. **[Configuration Guide](./06_CONFIGURATION.md)** — Settings, environment variables, and customization

### Data Management
8. **[Ontology Specification](./technical/ontology-specification.md)** — Detailed ID formats and validation rules
9. **[Schema Reference](./07_SCHEMA_REFERENCE.md)** — Database tables, relationships, and constraints
10. **[Data Sources](./08_DATA_SOURCES.md)** — External data integration and mapping strategies

## 🏗️ Architecture Decision Records (ADRs)

- **[0001: Food State Identity is Path](./adr/0001-foodstate-identity-is-path.md)** — Why we use paths instead of UUIDs
- **[0002: FDC as Evidence Not Identity](./adr/0002-fdc-as-evidence-not-identity.md)** — Evidence vs identity separation
- **[0003: Nutrient Mapping Strategy](./adr/0003-nutrient-mapping-strategy.md)** — FDC to INFOODS mapping approach

## 📖 Guides & References

### User Guides
- **[How to Add Food](./how-to-add-food.md)** — Step-by-step guide for adding new foods
- **[Search Guide](./09_SEARCH_GUIDE.md)** — How to effectively search the food graph
- **[Nutrition Queries](./10_NUTRITION_QUERIES.md)** — Querying nutrient data and profiles

### Developer Resources
- **[ETL Documentation](../etl/docs/)** — Detailed ETL pipeline documentation
- **[API Examples](./11_API_EXAMPLES.md)** — Code examples and integration patterns
- **[Testing Guide](./12_TESTING_GUIDE.md)** — Testing strategies and best practices

## 🔧 ETL Pipeline Documentation

The ETL (Extract, Transform, Load) pipeline documentation is located in the `etl/docs/` directory:

- **[ETL Overview](../etl/docs/00-overview.md)** — Pipeline architecture and data flow
- **[Stage Documentation](../etl/docs/02-stages.md)** — Detailed stage-by-stage documentation
- **[Configuration](../etl/docs/03-configuration.md)** — ETL configuration and customization
- **[Schemas](../etl/docs/04-schemas.md)** — Database schemas and data structures
- **[Testing](../etl/docs/05-testing.md)** — ETL testing and validation

## 📊 Data Sources

### External Data Integration
- **[FDC Foundation Import](./sources/FDC_FOUNDATION_IMPORT.md)** — USDA FoodData Central integration
- **[Canadian Nutrient File](./sources/CANADIAN_NF_IMPORT.md)** — Canadian nutrition data (planned)
- **[European Food Databases](./sources/EURO_FOOD_IMPORT.md)** — European nutrition data (planned)

## 🎯 Quick Reference

### Common Tasks
- **Add a new food**: See [How to Add Food](./how-to-add-food.md)
- **Query nutrition data**: See [Nutrition Queries](./10_NUTRITION_QUERIES.md)
- **Run the ETL pipeline**: See [ETL Overview](../etl/docs/00-overview.md)
- **Understand the data model**: See [Architecture Overview](./01_ARCHITECTURE.md)

### Key Concepts
- **Taxa (T)**: Biological sources (e.g., `tx:p:malus:domestica`)
- **Parts (P)**: Anatomical components (e.g., `part:fruit`)
- **Transforms (TF)**: Processing operations (e.g., `tf:ferment`)
- **TPT**: Transformed products (e.g., `tpt:tx:p:malus:domestica:part:fruit:FRESH:abc123`)

### File Locations
- **Ontology data**: `data/ontology/`
- **Evidence data**: `data/evidence/`
- **ETL code**: `etl/`
- **API code**: `apps/api/`
- **Web UI**: `apps/web/`

## 🤝 Contributing

We welcome contributions! Please see the [Development Guide](./05_DEVELOPMENT_GUIDE.md) for:
- Setting up your development environment
- Understanding the codebase structure
- Submitting changes and pull requests
- Testing and quality assurance

## 📞 Support

- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Join community discussions in GitHub Discussions
- **Documentation**: This documentation is continuously updated

---

**Note**: This documentation is actively maintained. If you find outdated information or have suggestions for improvement, please open an issue or submit a pull request.