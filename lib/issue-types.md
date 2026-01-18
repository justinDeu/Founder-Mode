# Issue Types

Normalized issue interface used across GitHub and Jira integrations.

## NormalizedIssue

```typescript
interface NormalizedIssue {
  source: "github" | "jira";
  id: string;           // "123" or "PROJ-123"
  url: string;          // Full URL to issue
  title: string;
  body: string;
  labels: string[];
  assignees: string[];
  milestone?: string;
  created: string;      // ISO timestamp
  updated: string;      // ISO timestamp
  // Jira-specific fields
  status?: string;      // "To Do", "In Progress", "Done"
  priority?: string;    // "High", "Medium", "Low"
  issueType?: string;   // "Bug", "Story", "Task"
  sprint?: string;      // Sprint name
  project?: string;     // Project key (PROJ)
}
```

## Parsing GitHub Response

From `gh issue view --json`:

```json
{
  "number": 123,
  "title": "Fix login redirect",
  "body": "Steps to reproduce...",
  "labels": [{"name": "bug"}],
  "assignees": [{"login": "user"}],
  "milestone": {"title": "v1.0"},
  "createdAt": "2026-01-18T10:00:00Z",
  "updatedAt": "2026-01-18T12:00:00Z"
}
```

Map to NormalizedIssue:

```
source: "github"
id: number.toString()
url: "https://github.com/{owner}/{repo}/issues/{number}"
title: title
body: body
labels: labels.map(l => l.name)
assignees: assignees.map(a => a.login)
milestone: milestone?.title
created: createdAt
updated: updatedAt
```
