"""Supabase Design Agent: designs the Supabase backend for a SaaS idea.

Produces tables, columns, relationships, Row Level Security policies, auth
setup, storage buckets, and SQL migrations based on the approved architecture.
"""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager

logger = logging.getLogger(__name__)


@dataclass
class SupabaseDesignAgent(BaseAgent):
    id: str = "supabase-design"
    name: str = "Supabase Design Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []
        idea_brief = context.artifacts.get("idea-generation", context.idea)
        plan_report = context.artifacts.get("plan", "")
        architecture = context.artifacts.get("architecture", "")
        execution_plan = context.artifacts.get("execution-plan", "")

        user_prompt = f"""Idea brief:
{idea_brief}

Plan report:
{plan_report}

Architecture design:
{architecture}

Execution plan:
{execution_plan}

Design a Supabase backend for this SaaS."""

        system_prompt = (
            "You are the Supabase Design Agent. Produce a complete Supabase design "
            "document with these sections:\n"
            "1. Overview — which Supabase features are used and why\n"
            "2. Project Setup — env variables (SUPABASE_URL, SUPABASE_ANON_KEY, etc.)\n"
            "3. Database Schema — tables, columns, types, primary/foreign keys, indexes\n"
            "4. Row Level Security (RLS) Policies — per table\n"
            "5. Auth Setup — providers, triggers, profiles table\n"
            "6. Storage Buckets — bucket names and access rules\n"
            "7. Edge Functions — list and purpose (if any)\n"
            "8. SQL Migrations — runnable SQL to create the schema\n\n"
            "Keep the design aligned with the architecture and execution plan."
        )

        fallback = f"""# Supabase Design

## Overview
Use Supabase as the managed backend: Postgres database, built-in Auth, Storage for files, and optional Edge Functions for serverless tasks.

## Project Setup
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (server-side only)

## Database Schema
- `profiles` (id UUID PRIMARY KEY, email TEXT, created_at TIMESTAMPTZ)
- `projects` or domain table depending on the idea.
- `runs` or audit log table.

## Row Level Security Policies
- `profiles`: users can read/update only their own row.
- Domain tables: owner-based access where applicable.

## Auth Setup
- Email/password provider enabled.
- Trigger to create a `profiles` row on `auth.users` insert.

## Storage Buckets
- `uploads` bucket with private access and owner-based RLS.

## Edge Functions
- None required for the MVP.

## SQL Migrations
```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own profile"
    ON profiles FOR ALL
    USING (auth.uid() = id);
```
"""

        content = call_llm(self.id, system_prompt, user_prompt, fallback)
        artifact_path = self.artifact_manager.write("supabase-design", content)
        logs.append(self.log(f"Wrote Supabase design to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[artifact_path],
            logs=logs,
            artifact_text=content,
        )
