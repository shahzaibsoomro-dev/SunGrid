# Coding Guidelines

Follow these guidelines for all code you write or modify in this project.

Prioritize simplicity, readability, and maintainability. Follow the existing project structure and conventions. Before adding new abstractions or changing architecture, inspect the existing code and prefer reusing what already exists.

If requirements are unclear or a change could significantly affect architecture or existing behavior, ask before implementing.

## Code Style

* Prefer simple, clean, readable Python over clever or abstract solutions.
* Keep functions small and focused on one responsibility.
* Use type hints for function arguments and return values.
* Avoid `Any` unless genuinely necessary.
* Avoid deeply nested `if/else`; use early returns where they improve readability.
* Don't add comments for obvious code. Comment why, not what.
* Keep major functions documented with a short 1–2 line docstring.

## Simplicity

* Don't over-engineer. Use the simplest solution that solves the requirement.
* Don't introduce classes, abstractions, interfaces, factories, registries, or design patterns unless there is a concrete need. Ask before using them.
* Don't create helper functions used only once unless they meaningfully improve readability.
* Reuse existing project utilities before creating new ones.
* Follow the existing project structure and conventions.

## Async

* Use `async` when the operation is actually I/O-bound/asynchronous.
* Use `asyncio.gather()` for multiple independent async operations that can safely run concurrently.
* Call function in batches where we need to many concurrent calls, do report me about it.
* Do not introduce threading, multiprocessing, background workers, or other concurrency mechanisms. Ask before using them.

## Error Handling

* Handle errors at the appropriate boundary.
* Add exception handling where needed and catch specific exceptions when possible.
* Keep logs and error messages short, clear, and actionable.

## APIs

* Use request/response schemas for API endpoints where relevant.
* Keep schemas minimal; don't duplicate fields or over-engineer them.
* Validate inputs where validation provides real value.
* Return appropriate HTTP status codes.

## Changes

* Make the smallest change necessary to solve the task.
* Don't refactor unrelated code.
* Don't modify working behavior outside the requested scope.
* Preserve existing APIs and behavior unless the task requires changing them.

## Testing

* Verify the affected functionality after making changes.
* Add tests for important business logic and non-trivial behavior.
* Don't add tests purely for coverage.