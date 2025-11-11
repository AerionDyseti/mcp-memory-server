# Simplification Cascades

Break complex problems into cascading layers of simpler problems until each piece is trivially solvable.

## Core Technique
Recursively decompose complex problems into simpler sub-problems until you reach trivial base cases.

## When Invoked
1. State the complex problem
2. Break into 2-5 simpler sub-problems
3. For each sub-problem, repeat step 2
4. Continue until problems are trivial
5. Solve from bottom up
6. Integrate solutions

## Example Cascade
Problem: Build e-commerce site
→ User auth + Product catalog + Cart + Checkout
  → User auth = Registration + Login + Sessions
    → Registration = Form + Validation + DB insert
      → Form = HTML + Client validation
      → (Now trivial - implement directly)

## Best Practices
- Each level should be clearly simpler
- Aim for 2-5 sub-problems per level
- Stop when problems become trivial
- Solve leaf nodes first, integrate upward
- Document the decomposition

## Resources
- [Divide and Conquer](https://en.wikipedia.org/wiki/Divide-and-conquer_algorithm)
