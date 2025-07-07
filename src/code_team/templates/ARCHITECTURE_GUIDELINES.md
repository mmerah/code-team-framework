# Architecture Guidelines

## Introduction
The goal of this architecture is to create a system that is maintainable, scalable, testable, and easy for new developers to understand. These principles are not optional; they are the foundation of our codebase and must be adhered to in all new and modified code.

## 1. Core Design Philosophies

-   **Keep It Simple, Stupid (KISS)**: Favor straightforward solutions. Code should be readable and easily understood by new developers. Avoid unnecessary complexity and clever "tricks." If a solution is hard to explain, it's probably the wrong solution.

-   **You Aren't Gonna Need It (YAGNI)**: Only implement features that are explicitly required by the current task. Do not add functionality based on anticipated future needs. This prevents code bloat and keeps the system focused.

-   **Don't Repeat Yourself (DRY)**: Abstract common logic into reusable functions, classes, or services. If you find yourself writing the same block of code a third time, it's a signal to refactor it into a reusable component.

## 2. Code Quality & Contracts

-   **Strong Typing & Explicit Contracts**: Write code that is clear, self-documenting, and robust. Always use the most specific type hint possible (e.g., `list[str]` instead of `list`). This allows projects to catch bugs before runtime, improves IDE autocompletion, and makes the code easier to reason about. All function signatures, class members, and variables should be typed.

## 3. SOLID Principles & Modularity

Create a system that is easy to maintain, extend, and test by adhering to SOLID principles.

-   **S - Single Responsibility Principle**: A class or module should have one, and only one, reason to change. For example, a `UserService` should handle user-related business logic, while a `UserRepository` should only handle database interactions for users.

-   **O - Open/Closed Principle**: Software entities should be open for extension, but closed for modification. Use abstractions, inheritance, or composition to add new functionality without changing existing, working code.

-   **L - Liskov Substitution Principle**: Subtypes must be substitutable for their base types without altering the correctness of the program. If you have a `BaseRepository` class, any class that inherits from it must implement all its methods in a compatible way.

-   **I - Interface Segregation Principle**: Clients should not be forced to depend on interfaces they do not use. Create small, focused interfaces (e.g., abstract base classes in Python) rather than large, monolithic ones.

-   **D - Dependency Inversion Principle**: This is the core of our architecture. High-level modules should not depend on low-level modules; both should depend on abstractions. For example, a high-level service should depend on a `RepositoryInterface` (an abstraction), not a concrete `PostgresRepository` (a detail). The concrete implementation is then injected at runtime.

## 4. API Design

-   **RESTful API Conventions**: Use plural, kebab-case nouns for resources (e.g., `/api/v1/user-profiles`). Use standard HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) to represent actions on those resources.

## 5. Naming and Structure

-   **Directory & File Naming**: Use `snake_case` for all directory and file names (e.g., `user_service.py`).
-   **Class Naming**: Use `PascalCase` (e.g., `UserService`).
-   **Function & Variable Naming**: Use `snake_case` (e.g., `get_user_by_id`).
-   **Descriptive Names**: Names should be descriptive and unambiguous. Avoid abbreviations. A longer, clearer name is better than a short, cryptic one.