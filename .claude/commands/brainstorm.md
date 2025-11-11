# Brainstorm

Explore feature feasibility and generate creative solutions.

## Purpose

The brainstorm command helps you explore possibilities, evaluate technical feasibility, and generate multiple approaches to solving problems. Unlike /plan which creates actionable steps, /brainstorm focuses on creative exploration, trade-off analysis, and discovering the best approach before committing to implementation.

## Usage

```
/brainstorm
```

With topic:
```
/brainstorm How to implement real-time collaboration in our document editor
```

## Workflow

1. **Problem Definition**: Clarifies the challenge or opportunity
2. **Context Gathering**: Analyzes current codebase, tech stack, and constraints
3. **Idea Generation**: Proposes multiple solution approaches
4. **Feasibility Analysis**: Evaluates each approach's pros and cons
5. **Technology Options**: Suggests relevant libraries, frameworks, or patterns
6. **Trade-off Discussion**: Compares solutions across dimensions (complexity, performance, cost)
7. **Recommendation**: Suggests the most promising approach with rationale
8. **Next Steps**: Outlines how to prototype or validate the chosen direction

## Best Practices

- Use brainstorm early in the feature development cycle
- Keep an open mind to unconventional solutions
- Consider non-technical constraints (budget, timeline, team skills)
- Ask follow-up questions to explore promising ideas deeper
- Document brainstorming outcomes for future reference
- Use insights to inform your /plan or /cook commands

## Examples

**Example 1: Architecture Decision**
```
/brainstorm Best approach for multi-tenant data isolation

Output:
- Option 1: Database per tenant (highest isolation, higher cost)
- Option 2: Schema per tenant (balanced approach)
- Option 3: Row-level security (lowest cost, shared schema)
- Trade-offs analysis
- Recommendation: Schema per tenant for your scale
- Migration path from current setup
```

**Example 2: User Experience**
```
/brainstorm Improve onboarding completion rate

Output:
- Interactive tutorials
- Progressive disclosure of features
- Gamification elements
- Personalized onboarding paths
- Analysis of drop-off points
- Quick wins vs. long-term improvements
- A/B testing strategy
```

**Example 3: Technical Challenge**
```
/brainstorm Handle large file uploads (>1GB) efficiently

Output:
- Chunked upload with resume capability
- Direct-to-S3 uploads with presigned URLs
- WebAssembly-based client-side processing
- Background processing pipeline
- Progress tracking approaches
- Error handling strategies
- Recommended: Chunked + S3 for scalability
```
