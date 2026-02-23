# Skills for EmergentDB

Skills extend what Claude Code can do with EmergentDB. Create a `SKILL.md` file with instructions, and Claude adds it to its toolkit — using it automatically when relevant, or on-demand via `/skill-name`.

## Quick Start

### Create a skill

```bash
mkdir -p .claude/skills/my-skill
```

Create `.claude/skills/my-skill/SKILL.md`:

```yaml
---
name: my-skill
description: What this skill does and when to use it
---

Your instructions here...
```

That's it. Claude will use the skill when your description matches what the user is asking.

## Example: Semantic Search Skill

A skill that teaches Claude to use EmergentDB for semantic search in your project:

```bash
mkdir -p .claude/skills/semantic-search
```

Create `.claude/skills/semantic-search/SKILL.md`:

```yaml
---
name: semantic-search
description: Search project knowledge base using EmergentDB vector similarity. Use when the user asks to find similar documents, search by meaning, or query the knowledge base.
allowed-tools: Bash
---

# Semantic Search

Use the EmergentDB Python SDK to search the project's vector database.

## Search for similar documents

```bash
python3 -c "
from emergentdb import EmergentDB
db = EmergentDB('$EMERGENTDB_API_KEY')

# Generate embedding for the query (use your preferred embedding model)
query_vector = get_embedding('$ARGUMENTS')

results = db.search(query_vector, k=5, include_metadata=True, namespace='docs')
for r in results.results:
    print(f'{r.score:.3f} | {r.metadata}')
db.close()
"
```

Return the top results with their relevance scores and metadata.
```

Now `/semantic-search how does authentication work` will trigger a vector search.

## Example: Index Documents Skill

```bash
mkdir -p .claude/skills/index-docs
```

Create `.claude/skills/index-docs/SKILL.md`:

```yaml
---
name: index-docs
description: Index documents into EmergentDB for later semantic search
disable-model-invocation: true
allowed-tools: Bash
---

# Index Documents

Index the specified files into EmergentDB using batch insert.

1. Read the files specified in $ARGUMENTS
2. Split into chunks (500 tokens each, 50 token overlap)
3. Generate embeddings using the project's embedding model
4. Batch insert into EmergentDB:

```bash
python3 -c "
from emergentdb import EmergentDB
db = EmergentDB('$EMERGENTDB_API_KEY')

vectors = []
for i, (chunk, embedding) in enumerate(chunks_and_embeddings):
    vectors.append({
        'id': start_id + i,
        'vector': embedding,
        'metadata': {'source': filename, 'chunk': chunk[:200]}
    })

result = db.batch_insert(vectors, namespace='docs')
print(f'Indexed {result.count} chunks')
db.close()
"
```
```

Since `disable-model-invocation: true` is set, this only runs when you type `/index-docs`.

## Example: Database Health Check

```yaml
---
name: db-health
description: Check EmergentDB connection and namespace status
allowed-tools: Bash
---

# Health Check

Check the EmergentDB API status and list available namespaces:

```bash
curl -s https://api.emergentdb.com/health | python3 -m json.tool

curl -s https://api.emergentdb.com/vectors/namespaces \
  -H "Authorization: Bearer $EMERGENTDB_API_KEY" | python3 -m json.tool
```

Report the status and available namespaces.
```

## Skill Configuration

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Slash command name (defaults to directory name) |
| `description` | Recommended | When to use this skill — Claude uses this to decide |
| `disable-model-invocation` | No | `true` = only runs via `/name`, Claude won't auto-trigger |
| `allowed-tools` | No | Tools Claude can use without asking permission |
| `context` | No | `fork` to run in an isolated subagent |
| `argument-hint` | No | Hint for autocomplete, e.g. `[query]` |

### String Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | Everything the user typed after `/skill-name` |
| `$ARGUMENTS[0]`, `$0` | First argument |
| `$ARGUMENTS[1]`, `$1` | Second argument |
| `` !`command` `` | Runs a shell command and injects the output |

### Where to Put Skills

| Location | Scope |
|----------|-------|
| `~/.claude/skills/<name>/SKILL.md` | All your projects (personal) |
| `.claude/skills/<name>/SKILL.md` | This project only (shareable via git) |

### Controlling Invocation

| Setting | You can invoke | Claude can invoke |
|---------|---------------|-------------------|
| Default | Yes | Yes |
| `disable-model-invocation: true` | Yes | No |
| `user-invocable: false` | No | Yes |

## Tips

- Keep `SKILL.md` under 500 lines. Use supporting files for reference material.
- Write descriptions that match how users naturally ask questions.
- Use `disable-model-invocation: true` for skills with side effects (indexing, deleting, deploying).
- Use `allowed-tools` to grant tool access without per-use permission prompts.
- Use `context: fork` for long-running tasks that shouldn't block the conversation.
- Add supporting files (templates, scripts, examples) in the skill directory and reference them from `SKILL.md`.
