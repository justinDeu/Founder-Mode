# Verification Patterns Reference

Patterns for verifying different artifact types. Used by `plan-checker` (pre-execution) and `verifier` (post-execution) agents.

## React Components

### Existence Checks

```bash
# Check component file exists
[ -f "src/components/ComponentName.tsx" ] && echo "EXISTS" || echo "MISSING"

# Check for default export
grep -E "^export default" "src/components/ComponentName.tsx"
```

### Substantive Checks

**Minimum lines:** 15+

**Stub patterns to detect:**

```javascript
// Empty renders
return null;
return <></>;
return <div></div>;
return <div>Component</div>;
return <div>Placeholder</div>;

// Missing implementation markers
// TODO: implement
// FIXME: add logic
{/* Placeholder */}

// Empty handlers
onClick={() => {}}
onChange={() => console.log('clicked')}
onSubmit={(e) => e.preventDefault()}
```

**Required content for real component:**

```bash
# Has JSX return
grep -E "return\s*\(" "$file"

# Has props destructuring or usage
grep -E "props\.|{.*}" "$file"

# Has state management (if interactive)
grep -E "useState|useReducer|useContext" "$file"
```

### Wiring Checks

```bash
# Is component imported somewhere?
grep -r "import.*ComponentName" src/ --include="*.tsx" --include="*.ts" | grep -v "$file"

# Is component rendered in JSX?
grep -r "<ComponentName" src/ --include="*.tsx" | grep -v "$file"
```

### Key Link Patterns

**Component -> API:**
```bash
# Check for fetch call
grep -E "fetch\(['\"].*api/" "$file"

# Check for axios call
grep -E "axios\.(get|post|put|delete)" "$file"

# Check response handling
grep -A 5 "fetch\|axios" "$file" | grep -E "await|\.then|setData|setState"
```

**Component -> State:**
```bash
# Check state is rendered
state_var="messages"
grep -E "useState.*$state_var|\[$state_var," "$file"
grep -E "\{.*$state_var.*\}|\{$state_var\." "$file"
```

---

## API Endpoints

### Existence Checks

```bash
# Next.js App Router
[ -f "src/app/api/resource/route.ts" ] && echo "EXISTS" || echo "MISSING"

# Check for HTTP method exports
grep -E "^export (async )?function (GET|POST|PUT|DELETE|PATCH)" "$file"
```

### Substantive Checks

**Minimum lines:** 10+

**Stub patterns to detect:**

```typescript
// Empty responses
return Response.json({});
return Response.json([]);
return Response.json({ ok: true });
return Response.json({ message: "Not implemented" });

// Console.log only
export async function POST(req) {
  console.log(await req.json());
  return Response.json({ ok: true });
}

// Static data (no database query)
export async function GET() {
  return Response.json([
    { id: 1, name: "Hardcoded" },
  ]);
}
```

**Required content for real endpoint:**

```bash
# Has database query
grep -E "prisma\.|db\.|findMany|findUnique|create|update|delete" "$file"

# Has proper error handling
grep -E "try\s*{|catch|throw" "$file"

# Returns query result
grep -E "return.*json.*await|return Response\.json\(.*\)" "$file"
```

### Wiring Checks

```bash
# Is endpoint called from frontend?
api_path="/api/resource"
grep -r "fetch.*$api_path\|axios.*$api_path" src/ --include="*.tsx" --include="*.ts"

# Does endpoint query database model?
model="Message"
grep -E "prisma\.$model|db\.$model" "$file"
```

### Key Link Patterns

**API -> Database:**
```bash
# Has query
grep -E "prisma\.(message|user|post)\.(find|create|update|delete)" "$file"

# Result is returned (not ignored)
grep -A 3 "prisma\." "$file" | grep -E "return.*json"
```

**API -> External Service:**
```bash
# Calls external API
grep -E "fetch\(['\"]https://|axios\.(get|post).*https://" "$file"

# Has API key/auth header
grep -E "Authorization:|api.key|API_KEY" "$file"
```

---

## Database Models

### Existence Checks

```bash
# Prisma schema
grep -E "^model\s+$model_name\s*{" prisma/schema.prisma

# Check for ID field
grep -A 20 "^model $model_name" prisma/schema.prisma | grep -E "id\s+.*@id"
```

### Substantive Checks

**Minimum lines:** 5+ (within model block)

**Stub patterns to detect:**

```prisma
// Empty model
model User {
  id Int @id
}

// Only placeholder fields
model Post {
  id Int @id
  // TODO: add fields
}
```

**Required content for real model:**

```bash
# Has multiple fields
grep -A 30 "^model $model_name" prisma/schema.prisma | grep -c "^\s\+\w"

# Has relationships (if applicable)
grep -A 30 "^model $model_name" prisma/schema.prisma | grep -E "@relation|references:"

# Has required fields for domain
grep -A 30 "^model $model_name" prisma/schema.prisma | grep -E "createdAt|updatedAt|String|Int|Boolean"
```

### Wiring Checks

```bash
# Is model used in API routes?
grep -r "prisma\.$model_name" src/ --include="*.ts"

# Is model exported/used in types?
grep -r "import.*$model_name\|type $model_name" src/ --include="*.ts"
```

---

## Configuration Files

### Existence Checks

```bash
# Check config file exists
[ -f "next.config.js" ] && echo "EXISTS" || echo "MISSING"
[ -f ".env.local" ] && echo "EXISTS" || echo "MISSING"
[ -f "tsconfig.json" ] && echo "EXISTS" || echo "MISSING"
```

### Substantive Checks

**Minimum lines:** 5+

**Stub patterns to detect:**

```javascript
// Empty config
module.exports = {};

// Placeholder values
const config = {
  // TODO: configure
};

// Missing required fields
// (depends on config type)
```

**Required content by config type:**

```bash
# next.config.js - has meaningful config
grep -E "reactStrictMode|images|experimental" next.config.js

# tsconfig.json - has compiler options
grep -E "compilerOptions|strict|paths" tsconfig.json

# .env - has required variables
grep -E "DATABASE_URL|NEXTAUTH_SECRET|API_KEY" .env.local
```

### Wiring Checks

```bash
# Are env vars used in code?
env_var="DATABASE_URL"
grep -r "process\.env\.$env_var|env\.$env_var" src/ --include="*.ts"
```

---

## CLI Commands

### Existence Checks

```bash
# Check command file exists
[ -f "src/cli/commands/command-name.ts" ] && echo "EXISTS" || echo "MISSING"

# Check command is exported
grep -E "^export (const|function|class)" "$file"
```

### Substantive Checks

**Minimum lines:** 20+

**Stub patterns to detect:**

```typescript
// Empty implementation
export function run() {
  console.log('Not implemented');
}

// Early exit
export function run() {
  process.exit(0);
}

// TODO markers
// TODO: implement this command

// Placeholder output
console.log('Command placeholder');
```

**Required content for real command:**

```bash
# Has argument parsing
grep -E "argv|args|yargs|commander|parseArgs" "$file"

# Has actual logic (not just logging)
grep -E "await|async|fs\.|path\.|exec" "$file"

# Has error handling
grep -E "try\s*{|catch|throw|process\.exit\(1\)" "$file"
```

### Wiring Checks

```bash
# Is command registered?
grep -r "command-name" src/cli/index.ts

# Is command in help text?
grep -r "command-name" src/cli/help.ts 2>/dev/null
```

---

## Tests

### Existence Checks

```bash
# Check test file exists
[ -f "src/components/__tests__/Component.test.tsx" ] && echo "EXISTS" || echo "MISSING"

# Check has test cases
grep -c "it\(|test\(" "$file"
```

### Substantive Checks

**Minimum lines:** 15+

**Stub patterns to detect:**

```typescript
// Empty tests
it('should work', () => {
  // TODO
});

// Skipped tests
it.skip('should do something', ...);
describe.skip('Component', ...);

// Tests that only log
it('works', () => {
  console.log('test');
});

// Tests with no assertions
it('renders', () => {
  render(<Component />);
});
```

**Required content for real tests:**

```bash
# Has assertions
grep -E "expect\(|assert\.|toBe|toEqual|toHaveBeenCalled" "$file"

# Has setup/teardown (if needed)
grep -E "beforeEach|afterEach|beforeAll|afterAll" "$file"

# Has meaningful descriptions
grep -E "it\(['\"]should|test\(['\"]" "$file"
```

### Wiring Checks

```bash
# Is test file in test config?
grep -r "testMatch\|testRegex" jest.config.js vitest.config.ts 2>/dev/null

# Does test import the module under test?
grep -E "import.*from.*\.\./.*Component" "$file"
```

---

## Hooks and Utilities

### Existence Checks

```bash
# Check hook file exists
[ -f "src/hooks/useHookName.ts" ] && echo "EXISTS" || echo "MISSING"

# Check for export
grep -E "^export (const|function)" "$file"
```

### Substantive Checks

**Minimum lines:** 10+

**Stub patterns to detect:**

```typescript
// Empty hook
export function useHook() {
  return null;
}

// Placeholder return
export function useHook() {
  return { loading: false, data: null };
}

// TODO only
export function useHook() {
  // TODO: implement
  return {};
}
```

**Required content for real hook:**

```bash
# Has React hooks usage
grep -E "useState|useEffect|useCallback|useMemo|useRef" "$file"

# Has return value
grep -E "return\s*{|return\s*\[" "$file"

# Has logic (not empty)
lines=$(wc -l < "$file")
[ "$lines" -gt 10 ] && echo "SUBSTANTIVE" || echo "THIN"
```

### Wiring Checks

```bash
# Is hook imported and used?
hook_name="useHookName"
grep -r "import.*$hook_name\|$hook_name()" src/ --include="*.tsx" --include="*.ts" | grep -v "$file"
```

---

## Quick Reference: Minimum Lines

| Artifact Type | Minimum Lines |
|--------------|---------------|
| React Component | 15 |
| API Route | 10 |
| Database Model | 5 |
| Config File | 5 |
| CLI Command | 20 |
| Test File | 15 |
| Hook/Utility | 10 |

## Quick Reference: Common Stub Patterns

| Pattern | Severity | Meaning |
|---------|----------|---------|
| `return null` | High | Empty render |
| `return {}` | High | Empty object return |
| `return []` | Medium | May be valid empty state |
| `TODO:` | Medium | Incomplete |
| `FIXME:` | Medium | Known issue |
| `console.log` only | High | Debug code, no logic |
| `e.preventDefault()` only | High | Empty form handler |
| `// implement` | High | Placeholder |
| `Not implemented` | High | Explicit stub |
| `Placeholder` | High | Explicit stub |
