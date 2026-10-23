# Second Brain Setup

## 1. Create your private copy

Use **Use this template** on GitHub, choose **Private**, and then clone your new repository:

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-BRAIN-REPO.git ~/brain
cd ~/brain
```

Do not put personal information into this public template repository.

## 2. Personalize the core files

Edit these files in order:

1. `CONTEXT.md`: identity, current priorities, and the map of the brain
2. `SOUL.md`: communication style and preferences
3. `RULES.md`: working rules and safety boundaries
4. `projects/INDEX.md`: active and completed projects
5. `wiki/index.md`: durable knowledge you want AI tools to reuse

Delete the placeholder text as you replace it.

## 3. Connect your AI tools

Add the following instruction to the global instruction file for each file-aware AI tool:

```text
Read ~/brain/CONTEXT.md before every session.
Treat it as the source of truth for my identity, preferences, rules,
projects, knowledge, and memory architecture.
Check ~/brain/projects/INDEX.md before starting new work.
```

This repository includes `AGENTS.md`, which Codex reads when working inside the folder.

## 4. Establish the habit

Before beginning work:

```bash
cat ~/brain/projects/INDEX.md
cat ~/brain/wiki/index.md
```

After meaningful work:

- update the relevant project page;
- record durable lessons in `LEARNINGS.md` or the wiki;
- add a short daily note in `log/daily/YYYY-MM-DD.md`;
- commit and push the changes.

## 5. Optional semantic memory

Markdown is enough for most people. Add Supabase only when you want to retrieve small decisions by meaning.

Create a Supabase project and run this in its SQL editor:

```sql
create extension if not exists vector;

create table if not exists thoughts (
  id uuid primary key default gen_random_uuid(),
  content text not null unique,
  embedding vector(1536),
  metadata jsonb default '{}',
  created_at timestamptz default now()
);

create or replace function upsert_thought(
  p_content text,
  p_payload jsonb default '{}'
)
returns thoughts language plpgsql as $$
declare result thoughts;
begin
  insert into thoughts (content, metadata)
  values (p_content, p_payload)
  on conflict do nothing
  returning * into result;

  if result is null then
    select * into result from thoughts
    where content = p_content order by created_at desc limit 1;
  end if;

  return result;
end;
$$;

create or replace function match_thoughts(
  query_embedding vector(1536),
  match_threshold float default 0.5,
  match_count int default 10
)
returns table(
  id uuid,
  content text,
  metadata jsonb,
  created_at timestamptz,
  similarity float
)
language sql stable as $$
  select t.id, t.content, t.metadata, t.created_at,
    1 - (t.embedding <=> query_embedding) as similarity
  from thoughts t
  where t.embedding is not null
    and 1 - (t.embedding <=> query_embedding) > match_threshold
  order by t.embedding <=> query_embedding
  limit match_count;
$$;
```

Copy the example environment file and add your own values:

```bash
cp .env.example .env
```

Then use:

```bash
python3 ~/brain/scripts/brain.py capture "Chose Postgres because the data is relational" --type decision --topic architecture
python3 ~/brain/scripts/brain.py search "database tradeoffs"
python3 ~/brain/scripts/brain.py list --days 7
```

The service-role key is powerful. Never commit `.env`, expose the key to a browser, or share it with another person.

## 6. Grow only when necessary

Good additions include:

- `wiki/`: compiled, cross-linked knowledge
- `raw/`: immutable source material
- `skills/`: reusable workflows
- `log/weekly/`: periodic synthesis

Start with the core files. The system compounds because you maintain it, not because it has many folders.
