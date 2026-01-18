# State Management Utilities

Patterns and utilities for managing founder-mode state.

## Atomic Update Pattern

State files must be updated atomically to prevent corruption during concurrent operations.

### Write Protocol

```bash
# 1. Write to temporary file
temp_file="${target_file}.tmp.$$"
echo "$content" > "$temp_file"

# 2. Atomic move
mv "$temp_file" "$target_file"
```

### Read-Modify-Write

When updating state files:

1. Read current state
2. Compute changes
3. Write complete new state atomically
4. Never append or patch in place

```markdown
# Correct: Read, compute, write complete
state = read_state()
state.position.plan += 1
write_state(state)  # Writes entire file

# Incorrect: Append or patch
echo "Plan: 3" >> STATE.md  # Don't do this
sed -i 's/Plan: 2/Plan: 3/' STATE.md  # Don't do this
```

## Progress Calculation

### Formula

```
progress = (completed_plans / total_plans) * 100
```

### Implementation

```python
def calculate_progress(roadmap):
    completed = 0
    total = 0

    for phase in roadmap.phases:
        for plan in phase.plans:
            total += 1
            if plan.status == "complete":
                completed += 1

    if total == 0:
        return 0

    return int((completed / total) * 100)
```

### Display Format

```
Progress: [####------] 40%
```

Rendering:

```python
def render_progress_bar(percentage, width=10):
    filled = int(percentage / 100 * width)
    empty = width - filled
    return f"[{'#' * filled}{'-' * empty}] {percentage}%"
```

## State Transitions

### Valid Status Progressions

```
Ready to plan -> Planning -> Ready to execute -> In progress -> Phase complete
```

### Phase Transitions

```
Phase N complete -> Phase N+1 ready to plan (or Phase N.1 if inserted)
```

### Plan Transitions

```
Plan A of B complete -> Plan A+1 of B (same phase)
Plan B of B complete -> Phase complete
```

## File Locking

For concurrent access scenarios:

```bash
# Acquire lock
lock_file="${state_file}.lock"
while ! mkdir "$lock_file" 2>/dev/null; do
    sleep 0.1
done

# Do work
update_state

# Release lock
rmdir "$lock_file"
```

## State Reading Utilities

### Get Current Phase

```bash
grep "^Phase:" .founder-mode/STATE.md | head -1 | sed 's/Phase: //'
```

### Get Progress Percentage

```bash
grep "^Progress:" .founder-mode/STATE.md | grep -oP '\d+(?=%)'
```

### Get Last Activity

```bash
grep "^Last activity:" .founder-mode/STATE.md | sed 's/Last activity: //'
```

## State Writing Utilities

### Update Position

```bash
update_position() {
    local phase=$1
    local plan=$2
    local status=$3

    # Read current state
    state=$(cat .founder-mode/STATE.md)

    # Update fields
    state=$(echo "$state" | sed "s/^Phase: .*/Phase: $phase/")
    state=$(echo "$state" | sed "s/^Plan: .*/Plan: $plan/")
    state=$(echo "$state" | sed "s/^Status: .*/Status: $status/")

    # Atomic write
    echo "$state" > .founder-mode/STATE.md.tmp
    mv .founder-mode/STATE.md.tmp .founder-mode/STATE.md
}
```

### Update Progress Bar

```bash
update_progress() {
    local completed=$1
    local total=$2

    local pct=$((completed * 100 / total))
    local filled=$((pct / 10))
    local empty=$((10 - filled))

    local bar="["
    for i in $(seq 1 $filled); do bar+="#"; done
    for i in $(seq 1 $empty); do bar+="-"; done
    bar+="] ${pct}%"

    # Update in state file
    sed -i "s/^Progress: .*/Progress: $bar/" .founder-mode/STATE.md
}
```

### Record Activity

```bash
record_activity() {
    local description=$1
    local date=$(date +%Y-%m-%d)

    sed -i "s/^Last activity: .*/Last activity: $date - $description/" .founder-mode/STATE.md
}
```

## Validation Utilities

### Validate State File

Check STATE.md has required sections:

```bash
validate_state() {
    local file=".founder-mode/STATE.md"

    required_sections=(
        "## Project Reference"
        "## Current Position"
        "## Performance Metrics"
        "## Accumulated Context"
        "## Session Continuity"
    )

    for section in "${required_sections[@]}"; do
        if ! grep -q "$section" "$file"; then
            echo "Missing: $section"
            return 1
        fi
    done

    return 0
}
```

### Validate Roadmap Consistency

Ensure ROADMAP.md progress matches STATE.md:

```bash
validate_consistency() {
    # Extract phase from STATE.md
    state_phase=$(grep "^Phase:" .founder-mode/STATE.md | grep -oP '\d+' | head -1)

    # Check ROADMAP.md has that phase in progress
    roadmap_status=$(grep "Phase $state_phase" .founder-mode/ROADMAP.md | grep -oP 'In progress|Complete')

    if [[ "$roadmap_status" != "In progress" ]]; then
        echo "State/Roadmap mismatch: Phase $state_phase"
        return 1
    fi

    return 0
}
```

## Session Continuity

### Save Session State

Called when pausing work:

```bash
save_session() {
    local stopped_at=$1

    local timestamp=$(date "+%Y-%m-%d %H:%M")

    cat >> .founder-mode/STATE.md.tmp << EOF
## Session Continuity

Last session: $timestamp
Stopped at: $stopped_at
Resume file: None
EOF

    # Atomic update
    mv .founder-mode/STATE.md.tmp .founder-mode/STATE.md
}
```

### Create Continue-Here File

For mid-work pauses:

```bash
create_continue_here() {
    local context=$1

    local file=".founder-mode/continue-here-$(date +%Y%m%d-%H%M%S).md"

    cat > "$file" << EOF
# Continue Here

Created: $(date "+%Y-%m-%d %H:%M")

## Context

$context

## Next Steps

1. [First thing to do]
2. [Second thing to do]

## Notes

[Any important information]
EOF

    # Update STATE.md to reference this file
    sed -i "s|^Resume file: .*|Resume file: $file|" .founder-mode/STATE.md
}
```

## Todo Management

### Add Todo

```bash
add_todo() {
    local title=$1
    local description=$2
    local source=$3

    local slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
    local file=".founder-mode/todos/pending/$(date +%Y-%m-%d-%H-%M)-${slug}.md"

    mkdir -p .founder-mode/todos/pending

    cat > "$file" << EOF
# $title

Created: $(date "+%Y-%m-%d %H:%M")
Source: $source

## Description

$description
EOF

    echo "$file"
}
```

### Complete Todo

```bash
complete_todo() {
    local todo_file=$1

    mkdir -p .founder-mode/todos/done

    local filename=$(basename "$todo_file")
    mv "$todo_file" ".founder-mode/todos/done/$filename"
}
```

### Count Pending Todos

```bash
count_pending_todos() {
    find .founder-mode/todos/pending -name "*.md" 2>/dev/null | wc -l
}
```
