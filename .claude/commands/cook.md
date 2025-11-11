# Cook

Develop new features from start to finish.

## Purpose

The cook command is your primary tool for feature development. It guides you through the complete lifecycle of building a new feature, from planning and design to implementation and testing. Think of it as a comprehensive workflow that "cooks" your feature to completion, ensuring nothing is missed along the way.

## Usage

```
/cook
```

With feature description:
```
/cook Add user authentication with OAuth providers
```

## Workflow

1. **Feature Analysis**: Understands the feature requirements and scope
2. **Technical Planning**: Identifies affected files, dependencies, and architecture changes
3. **Design Review**: Plans component structure, data models, and API contracts
4. **Implementation**: Writes code following best practices and project patterns
5. **Testing**: Creates unit and integration tests for the new feature
6. **Documentation**: Updates relevant docs and adds inline code comments
7. **Integration**: Ensures feature integrates smoothly with existing code
8. **Review Checklist**: Provides a summary of changes and testing recommendations

## Best Practices

- Provide clear, specific feature descriptions
- Review the technical plan before implementation begins
- Let the command complete fully for complex features
- Test edge cases and error scenarios
- Review generated code for alignment with project standards
- Update documentation as part of the feature development

## Examples

**Example 1: Authentication Feature**
```
/cook Implement JWT-based authentication with refresh tokens

Output:
- Creates auth middleware
- Adds login/logout endpoints
- Implements token refresh logic
- Adds authentication tests
- Updates API documentation
```

**Example 2: Data Export Feature**
```
/cook Add CSV and JSON export functionality for reports

Output:
- Creates export service
- Adds export API endpoints
- Implements format converters
- Adds download UI components
- Creates export tests
```

**Example 3: Real-time Notifications**
```
/cook Implement WebSocket-based real-time notifications

Output:
- Sets up WebSocket server
- Creates notification service
- Adds client-side listeners
- Implements notification UI
- Adds integration tests
```
