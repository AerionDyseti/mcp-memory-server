# /auto-feature - Automated Feature Implementation

**IMPORTANT**: This command activates the complete feature orchestration workflow. It combines semantic analysis, intelligent task generation, agent delegation, and automated implementation.

## Usage

```bash
/auto-feature <feature description>
```

## Examples

```bash
/auto-feature Build a user dashboard with activity charts and export to PDF

/auto-feature Add real-time notifications system with WebSocket

/auto-feature Create an admin panel for managing users and permissions

/auto-feature Implement invoice generation with PDF export and email delivery
```

## Workflow Overview

```
User Description
      ↓
[Phase 1] Semantic Analysis & Planning
      ↓
[Phase 2] Task Graph Generation
      ↓
[Phase 3] Agent Orchestration
      ↓
[Phase 4] Implementation
      ↓
[Phase 5] Integration & Testing
      ↓
[Phase 6] Documentation
      ↓
Complete Feature ✨
```

---

## Phase 1: Semantic Analysis & Planning

When the user invokes this command, immediately activate the **feature-orchestration** skill and perform:

### 1.1 Deep Analysis
Analyze the feature description to detect:
- **Feature Type**: CRUD, Analytics, Integration, Workflow, Real-time, etc.
- **Components Required**: UI, API, Database, Authentication, File handling, etc.
- **Complexity Level**: Simple, Medium, Complex, Very Complex
- **Technology Stack**: Frontend tech, Backend tech, Database needs

### 1.2 Requirements Generation
Create detailed requirements:
```markdown
# Feature: {Feature Name}

## Overview
{1-2 sentence summary}

## Functional Requirements
1. {Requirement 1}
2. {Requirement 2}
...

## Non-Functional Requirements
- Performance: {performance criteria}
- Security: {security requirements}
- Scalability: {scalability needs}

## Technical Requirements
- Frontend: {frontend stack}
- Backend: {backend stack}
- Database: {database changes}
- Testing: {test coverage requirements}
```

### 1.3 System Design
Generate high-level design:
```markdown
# System Design

## Architecture
{Architecture diagram in ASCII}

## Data Models
{Database schema}

## API Design
{API endpoints and contracts}

## Component Structure
{Component hierarchy}

## Integration Points
{How components connect}
```

---

## Phase 2: Task Graph Generation

Generate an optimized task breakdown with dependency management:

### 2.1 Task Detection Algorithm

```javascript
// Pseudo-code for task generation
const tasks = [];

// Critical path: Database (highest priority)
if (needsDatabase) {
  tasks.push({
    id: 'db-schema',
    agent: '@data-agent',
    priority: 'critical',
    dependencies: [],
    parallel: false
  });
}

// High priority: Backend (depends on DB)
if (needsAPI) {
  tasks.push({
    id: 'api-endpoints',
    agent: '@api-agent',
    priority: 'high',
    dependencies: needsDatabase ? ['db-schema'] : [],
    parallel: !needsDatabase
  });
}

// High priority: Frontend (can run parallel with backend)
if (needsUI) {
  tasks.push({
    id: 'ui-components',
    agent: '@ui-agent',
    priority: 'high',
    dependencies: [],
    parallel: true // Can start immediately with mock data
  });
}

// Medium priority: Integration (depends on UI + API)
if (needsUI && needsAPI) {
  tasks.push({
    id: 'integration',
    agent: '@api-agent',
    priority: 'medium',
    dependencies: ['ui-components', 'api-endpoints'],
    parallel: false
  });
}

// Medium priority: Testing (depends on everything)
tasks.push({
  id: 'testing',
  agent: '@qa-agent',
  priority: 'medium',
  dependencies: allPreviousTasks,
  parallel: false
});

// Low priority: Documentation
tasks.push({
  id: 'documentation',
  agent: '@orchestrator',
  priority: 'low',
  dependencies: ['testing'],
  parallel: false
});
```

### 2.2 Display Task Plan

Present the task plan to the user:

```
🎯 Feature Implementation Plan

Feature: {Feature Name}
Complexity: {complexity}
Estimated Time: {total time}

📋 Task Breakdown:

Wave 1 (Parallel Execution):
  ✓ Task 1: Database Schema Design
    Agent: @data-agent
    Time: ~20min
    Status: Ready to start

Wave 2 (Parallel Execution):
  ✓ Task 2: API Endpoints
    Agent: @api-agent
    Time: ~30min
    Depends on: Task 1

  ✓ Task 3: UI Components
    Agent: @ui-agent
    Time: ~40min
    No dependencies (can start with Task 2)

Wave 3 (Sequential):
  ✓ Task 4: Integration
    Agent: @api-agent
    Time: ~15min
    Depends on: Task 2, Task 3

Wave 4 (Sequential):
  ✓ Task 5: Testing
    Agent: @qa-agent
    Time: ~30min
    Depends on: Task 4

Wave 5 (Sequential):
  ✓ Task 6: Documentation
    Agent: @orchestrator
    Time: ~10min
    Depends on: Task 5

Total Estimated Time: ~2 hours 25 minutes

Proceed with implementation? (y/n)
```

---

## Phase 3: Agent Orchestration

**CRITICAL**: Use the Task tool to launch specialized agents. Each agent receives full context and specific instructions.

### 3.1 Agent Delegation Template

For each task, launch the appropriate agent:

```
Launching {agent-name} for {task-id}...

=== TASK CONTEXT ===
Feature: {feature name}
Task ID: {task-id}
Task Description: {task description}
Priority: {priority}
Estimated Time: {time}

=== COMPLETED DEPENDENCIES ===
{list of completed tasks with their outputs}

=== YOUR MISSION ===
{specific instructions for this agent}

=== EXPECTED DELIVERABLES ===
- {deliverable 1}
- {deliverable 2}
...

=== INTEGRATION REQUIREMENTS ===
{how this task connects with others}

=== CONSTRAINTS ===
- Technology: {tech stack}
- Code Style: {code style guide}
- Testing: {test requirements}
- Security: {security requirements}

Please implement this task following best practices. Report progress and any blockers.
```

### 3.2 Execution Waves

Execute tasks in waves based on dependencies:

```python
# Pseudo-code for wave execution
while (tasks_remaining):
  # Get tasks with satisfied dependencies
  ready_tasks = tasks.filter(t =>
    t.dependencies.every(d => d.completed)
  )

  # Group by wave (parallel vs sequential)
  parallel_tasks = ready_tasks.filter(t => t.parallel)
  sequential_tasks = ready_tasks.filter(t => !t.parallel)

  # Execute parallel tasks simultaneously
  if (parallel_tasks.length > 0):
    await Promise.all(
      parallel_tasks.map(task => launchAgent(task))
    )

  # Execute sequential tasks one by one
  for (task of sequential_tasks):
    await launchAgent(task)

  # Mark completed
  ready_tasks.forEach(t => t.completed = true)
```

---

## Phase 4: Implementation

### 4.1 Agent Specialization

**@data-agent** handles:
- Database schema design
- Migration scripts
- Model definitions
- Database indexes
- Data validation rules

**@api-agent** handles:
- REST API endpoints
- Business logic
- Request/response validation
- Error handling
- API documentation
- Authentication/authorization

**@ui-agent** handles:
- React components
- Tailwind CSS styling
- Form handling
- State management
- Client-side validation
- Accessibility

**@qa-agent** handles:
- Unit tests (Jest/Vitest)
- Integration tests
- E2E tests
- Test coverage
- Edge cases

### 4.2 Progress Tracking

Display real-time progress:

```
🚀 Implementation Progress

┌─────────────────────────────────────────┐
│  Feature: User Dashboard                │
│  Progress: [████████░░] 80%            │
└─────────────────────────────────────────┘

✅ Completed (3/6):
  ✓ Database Schema (18min)
    - Added dashboard_stats table
    - Created indexes for performance

  ✓ API Endpoints (28min)
    - GET /api/dashboard/stats
    - GET /api/dashboard/activity
    - POST /api/dashboard/export

  ✓ UI Components (42min)
    - Dashboard.jsx (with charts)
    - ActivityChart.jsx
    - StatsCard.jsx

🔄 In Progress (1/6):
  ⟳ Integration (@api-agent, 8/15min)
    - Connecting Dashboard to API
    - Adding loading states
    - Error handling

⏳ Pending (2/6):
  ⏸ Testing (@qa-agent)
  ⏸ Documentation (@orchestrator)

⏱ Time Elapsed: 1h 36min
⏱ Est. Remaining: 49min
```

---

## Phase 5: Integration & Testing

### 5.1 Integration
After individual tasks complete, integrate them:

```
🔗 Integration Phase

Connecting components:
  ✓ Frontend → Backend API
  ✓ Backend → Database
  ✓ Error handling
  ✓ Loading states
  ✓ Validation flow

Running integration checks:
  ✓ Data flow: UI → API → DB → API → UI
  ✓ Error propagation
  ✓ Edge cases
```

### 5.2 Testing
Launch @qa-agent for comprehensive testing:

```
🧪 Testing Phase

Unit Tests:
  ✓ Dashboard component renders correctly
  ✓ API endpoints return expected data
  ✓ Database queries are optimized

Integration Tests:
  ✓ Dashboard loads data from API
  ✓ Export generates correct PDF
  ✓ Error handling works end-to-end

E2E Tests:
  ✓ User can view dashboard
  ✓ Charts display activity data
  ✓ Export button downloads PDF

Coverage: 94% ✅ (target: 80%)
```

---

## Phase 6: Documentation

Generate comprehensive documentation:

### 6.1 Feature Documentation

```markdown
# Feature: User Dashboard

## Overview
A comprehensive dashboard displaying user activity with interactive charts and PDF export capability.

## Components

### Frontend
- `Dashboard.jsx` - Main dashboard component
- `ActivityChart.jsx` - Chart visualization
- `StatsCard.jsx` - Stat display cards

### Backend
- `GET /api/dashboard/stats` - Retrieve dashboard statistics
- `GET /api/dashboard/activity` - Get activity data for charts
- `POST /api/dashboard/export` - Generate PDF export

### Database
- `dashboard_stats` table - Stores aggregated statistics
- Indexes on `user_id`, `created_at` for performance

## Usage

```jsx
import Dashboard from './components/Dashboard';

function App() {
  return <Dashboard userId={currentUser.id} />;
}
```

## Testing
- Unit tests: `Dashboard.test.jsx`, `api.test.js`
- Integration tests: `dashboard-integration.test.js`
- E2E tests: `dashboard.e2e.test.js`

## Performance
- Initial load: < 500ms
- Chart rendering: < 200ms
- PDF generation: < 2s

## Security
- API endpoints require authentication
- User can only access their own dashboard
- PDF export is rate-limited
```

### 6.2 Update Project README

Add feature to main README:

```markdown
## Features

- ✅ User Dashboard
  - Interactive activity charts
  - Real-time statistics
  - PDF export functionality
  - Responsive design
```

---

## Final Report

Present completion summary to user:

```
✨ Feature Complete!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  User Dashboard with Charts & Export
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Summary:
  ✅ 6/6 tasks completed
  ✅ All tests passing (94% coverage)
  ✅ Documentation generated
  ⏱ Total time: 2h 23min (2min ahead of schedule!)

📁 Files Created/Modified:
  Backend (3 files):
    - src/server/routes/dashboard.js (new)
    - src/server/models/DashboardStats.js (new)
    - migrations/add_dashboard_stats.sql (new)

  Frontend (4 files):
    - src/components/Dashboard.jsx (new)
    - src/components/ActivityChart.jsx (new)
    - src/components/StatsCard.jsx (new)
    - src/App.jsx (modified)

  Tests (3 files):
    - tests/Dashboard.test.jsx (new)
    - tests/dashboard.e2e.test.js (new)
    - tests/api/dashboard.test.js (new)

  Documentation (1 file):
    - docs/features/dashboard.md (new)

🧪 Test Results:
  ✓ 24 unit tests passed
  ✓ 8 integration tests passed
  ✓ 5 E2E tests passed
  ✓ Coverage: 94%

🚀 Next Steps:
  1. Review the implementation
  2. Run `npm test` to verify all tests pass
  3. Start dev server: `npm run dev`
  4. Navigate to /dashboard to see the feature
  5. Deploy when ready!

📖 Documentation:
  - Feature docs: docs/features/dashboard.md
  - API docs: Updated in Swagger/OpenAPI
  - Component docs: Added JSDoc comments

Would you like me to:
  - Show you the code for any specific component?
  - Explain any implementation decisions?
  - Make adjustments to the feature?
  - Deploy to staging?
```

---

## Error Handling

If any task fails or encounters blockers:

```
⚠️ Blocker Detected

Task: API Endpoints (@api-agent)
Error: Database migration failed

Details:
  Column 'activity_score' already exists in dashboard_stats table

Options:
  1. Skip this column (use existing)
  2. Rename to 'activity_score_v2'
  3. Drop and recreate table (⚠️ data loss)
  4. Manual resolution

What would you like to do? (1-4)
```

Handle gracefully and get user input when needed.

---

## Best Practices

1. **Always show the plan first** - Get user approval before implementing
2. **Keep user informed** - Regular progress updates
3. **Use parallel execution** - Launch independent tasks simultaneously
4. **Track dependencies** - Never start a task too early
5. **Test thoroughly** - Don't skip testing phase
6. **Document everything** - Generate docs automatically
7. **Handle errors gracefully** - Ask user when blocked
8. **Celebrate completion** - Show clear success summary

---

## Advanced Features

### Pattern Recognition
If similar features were built before:
```
💡 Insight: This feature is similar to the "Reports Dashboard" built last week.

   Reusable components:
   - ChartWrapper.jsx
   - ExportService.js

   This could save ~30 minutes. Use existing components? (y/n)
```

### Adaptive Planning
If tasks take longer than expected:
```
⏱ Timeline Update

Original estimate: 2h 25min
Current progress: 1h 45min elapsed, 60% complete
Revised estimate: 2h 50min (+25min)

Reason: Integration phase more complex than expected (authentication requirements)

Continue? (y/n)
```

### Quality Gates
Enforce quality standards:
```
🚨 Quality Gate Failed

Test coverage: 72% (required: 80%)

Missing coverage in:
  - Dashboard.jsx: handleExport() function
  - api/dashboard.js: error handling paths

Generate additional tests? (y/n)
```

---

## Notes

- This command requires the `feature-orchestration` skill to be enabled
- Specialized agents must be configured in `.claude/config.json`
- Use Task tool for agent delegation
- All code follows project conventions (see CLAUDE.md)
- Generated code includes proper error handling, validation, and tests
- Documentation is generated automatically but can be customized

---

**Remember**: This is a fully automated workflow. Once started, it will run to completion with minimal user intervention (only for approvals or blockers). Trust the orchestration!
