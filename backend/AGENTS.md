# Backend Instructions

- Language: Python 3.12.
- API: FastAPI.
- Validation: Pydantic models at every boundary.
- Database: SQLAlchemy 2 async + PostgreSQL/PostGIS; migrations through Alembic.
- Runtime agents: OpenAI Agents SDK.
- Each runtime agent has independent instructions, tools and structured output.
- Specialist agents are invoked with separate Runner calls and scoped context.
- Do not share full chat transcripts with specialists unless their contract requires it.
- Deterministic concerns such as distance calculation, opening-hours parsing, ranking and authorization are services, not agents.
- Every external provider sits behind an adapter interface.
- All tool calls must have timeouts, error normalization and observability.
- Never log raw voice audio, access tokens or exact location history.
