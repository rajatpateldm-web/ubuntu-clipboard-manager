# Engineering Skills: Clean, DRY, and Secure Code

This guide provides practical standards for software development across the project. It establishes conventions for writing clean code, applying the Don't Repeat Yourself (DRY) principle, and developing secure code that protects user data and system integrity.

## 1. Writing Clean Code

Clean code is readable, simple, and maintainable. It minimizes cognitive load for teammates and future maintainers.

### Core Principles

*   **Readability counts:** Write code that clearly explains what it does. Grounded in [PEP 20 (The Zen of Python)](https://peps.python.org/pep-0020/), readability takes precedence over clever one-liners or dense shortcuts.
*   **Single Responsibility Principle:** Each function, class, and module must address exactly one concern. As defined in [Robert C. Martin's Clean Code principles](https://en.wikipedia.org/wiki/Clean_Code), a function should do one thing and do it well.
*   **Predictability:** Methods must produce expected side effects only. Avoid hidden state mutations or surprising behaviors.

### Meaningful Naming Conventions

*   **Variables and attributes:** Use descriptive nouns that reflect the stored data (for example, `clipboard_history`, `raw_text`, `is_pinned`). Avoid single-letter names except for standard loop indices (`i`, `j`).
*   **Functions and methods:** Use clear verb phrases that describe the action (for example, `save_item`, `normalize_text`, `is_sensitive_format`).
*   **Classes:** Use PascalCase nouns representing entities or services (for example, `ClipboardService`, `DatabaseService`, `MainWindow`).
*   **Constants:** Use UPPER_SNAKE_CASE for immutable module-level constants (for example, `MAX_HISTORY_ITEMS`, `SOCKET_TIMEOUT_MS`).

### Function Design and Complexity

*   **Keep functions small:** Aim for functions under 30 lines where practical. If a function handles multiple phases (parsing, validating, storing), divide each phase into a helper.
*   **Limit function parameters:** Restrict arguments to three or fewer. When more arguments are required, group related options into a dedicated dataclass, dictionary, or configuration object.
*   **Avoid flag arguments:** Passing boolean flags (for example, `process_data(data, True)`) indicates that the function performs two different jobs. Split them into distinct functions instead.
*   **Return early:** Use guard clauses at the beginning of functions to handle validation errors and edge cases early, reducing indentation depth.

### Explicit Error Handling

*   **Catch specific exceptions:** Never use bare `except:` or catch generic `Exception` unless logging before re-raising. Catch targeted errors like `sqlite3.OperationalError` or `subprocess.SubprocessError`.
*   **Never swallow errors silently:** Do not use `except: pass` without explicit logging and documented justification.
*   **Use context managers:** Always manage resources (files, database connections, sockets) using `with` statements to guarantee prompt closure even when exceptions arise.

### Self-Documenting Code and Comments

*   **Code as primary documentation:** Strive to make variable and function names explain the mechanism.
*   **Comments explain the reason:** Use docstrings and comments exclusively to explain why an approach was taken, architectural decisions, external constraints, or platform quirks.
*   **Keep comments current:** When updating code logic, update corresponding docstrings and comments in the same commit.

## 2. Do Not Repeat Yourself (DRY)

The DRY principle states that every piece of knowledge must have a single, unambiguous, authoritative representation within a system, as introduced in [The Pragmatic Programmer by Andy Hunt and Dave Thomas](https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/).

### Single Source of Truth

*   **Centralized configuration:** Define shared paths, timeout limits, port numbers, and UI dimensions in a dedicated configuration or constants module rather than duplicating literals across files.
*   **Unified data schemas:** Define database column names and data structures in one place to avoid mismatch bugs across persistence and UI layers.
*   **Shared business logic:** Normalize data formats (such as line ending normalization, whitespace stripping, and format verification) through centralized helper functions.

### Avoiding Duplication in Common Layers

*   **Database interactions:** Consolidate SQL queries and transaction patterns within dedicated service classes rather than inlining SQLite executions inside UI components.
*   **Platform checks:** Centralize operating system and session detection logic (such as Wayland versus X11 detection) in utility helpers rather than checking environment variables repeatedly.
*   **Validation routines:** Re-use shared validation functions for checking text lengths, MIME types, and file formats across both background workers and UI listeners.

### Balancing DRY with AHA Programming

*   **Avoid Hasty Abstractions:** As articulated in [Kent C. Dodds' AHA programming guide](https://kentcdodds.com/blog/aha-programming), premature abstraction is more costly than temporary duplication.
*   **The Rule of Three:** Wait until code is duplicated in three independent places before abstracting it into a shared helper or base class.
*   **Domain separation:** Do not combine two similar pieces of code if they represent distinct business domains that will evolve in different directions.

## 3. Writing Secure Code

Security must be integrated at every phase of development. Following the [OWASP Secure Coding Practices Quick Reference](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/) and [SEI CERT Python Coding Standard](https://wiki.sei.cmu.edu/confluence/display/python/SEI+CERT+Python+Coding+Standard), prioritize defensive programming to guard against vulnerabilities.

### Input Validation and Sanitization

*   **Never trust external input:** Treat data from clipboards, IPC sockets, environment variables, and user input as untrusted.
*   **Sanitize strings:** Strip null bytes, standardize line endings, and validate payload sizes before passing text to databases, logs, or system calls.
*   **Enforce length boundaries:** Check input length to prevent denial-of-service conditions or unbounded memory usage when storing clipboard data.

### Preventing Injection Attacks

*   **Parameterized SQL queries:** Never construct SQL queries with string concatenation or f-strings ([CWE-89](https://cwe.mitre.org/data/definitions/89.html)). Always pass values through parameter placeholders (`?` in SQLite):
    ```python
    # Secure:
    cursor.execute(
        "INSERT INTO clipboard_history (id, text, timestamp) VALUES (?, ?, ?)",
        (item_id, text, timestamp)
    )
    ```
*   **Avoid shell execution:** Avoid using `shell=True` in `subprocess` invocations to mitigate command injection risks ([CWE-78](https://cwe.mitre.org/data/definitions/78.html) and [Python subprocess security guidelines](https://docs.python.org/3/library/subprocess.html#security-considerations)).
*   **Use argument arrays:** Always pass executable commands and flags as lists of discrete strings:
    ```python
    # Secure:
    subprocess.run(["wl-paste", "--no-newline"], capture_output=True, check=True)
    ```
*   **Verify executable paths:** Validate binary locations using `shutil.which` before attempting execution.

### Protection of Sensitive Data

*   **Detect password manager data:** Inspect MIME types and metadata for sensitive content hints (such as `x-kde-passwordManagerHint`, `application/x-copyq-secret`, or `application/x-password-manager-hint`) to exclude secrets from persistent history.
*   **Secure file permissions:** When creating database files, cache stores, or IPC sockets, ensure appropriate file system permissions (for example, `0o600` for files, `0o700` for directories) so only the owner has read and write access.
*   **Protect credentials in logs:** Never print or log raw sensitive clipboard contents, API keys, passwords, or tokens.
*   **Zero out or clear sensitive buffers:** Ensure sensitive temporary objects are discarded promptly when no longer needed.

### Secure Inter-Process Communication (IPC)

*   **Local socket scoping:** Use scoped local sockets with unique names (such as `QLocalServer`) rather than listening on open network interfaces.
*   **Validate incoming IPC commands:** Verify payload syntax and reject unauthenticated or malformed instructions before executing actions.
*   **Handle stale sockets cleanly:** Clean up stale socket descriptors safely upon server startup without leaving open permissions.

### Information Disclosure Prevention

*   **Sanitized user messages:** Display user-friendly error notices in the UI without exposing internal tracebacks, local absolute paths, or database structures.
*   **Structured logging:** Route debugging output through standard logging frameworks with configurable log levels (DEBUG, INFO, WARNING, ERROR).

## 4. Engineering Standards Checklist

Review this checklist during development and before submitting code changes:

### Clean Code
*   [ ] Functions and variables have clear, intention-revealing names.
*   [ ] Functions perform a single task and contain minimal branching.
*   [ ] Guard clauses are used to handle edge cases and reduce nesting.
*   [ ] Resources are managed using context managers (`with` blocks).
*   [ ] Exceptions are targeted specifically, without bare `except` blocks.
*   [ ] Type annotations are provided for function signatures.

### DRY (Don't Repeat Yourself)
*   [ ] Literals, magic numbers, and strings are extracted to constants.
*   [ ] Common operations (normalization, validation, parsing) use shared utilities.
*   [ ] Database schema definitions and queries are centralized.
*   [ ] Code is abstracted only after genuine duplication exists (Rule of Three).

### Secure Code
*   [ ] External inputs are validated, stripped of null bytes, and bounded in size.
*   [ ] SQL statements use parameterized queries exclusively.
*   [ ] Subprocess executions avoid `shell=True` and pass argument lists.
*   [ ] Sensitive data and password manager hints are detected and excluded from persistence.
*   [ ] File permissions restrict access to the current user.
*   [ ] Error messages to users contain no internal system paths or tracebacks.

## 5. Primary References

*   [PEP 8 Style Guide for Python Code](https://peps.python.org/pep-0008/)
*   [PEP 20 The Zen of Python](https://peps.python.org/pep-0020/)
*   [PEP 484 Type Hints](https://peps.python.org/pep-0484/)
*   [OWASP Secure Coding Practices Quick Reference Guide](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
*   [Python Documentation on Subprocess Security](https://docs.python.org/3/library/subprocess.html#security-considerations)
*   [SEI CERT Python Coding Standard](https://wiki.sei.cmu.edu/confluence/display/python/SEI+CERT+Python+Coding+Standard)
*   [The Pragmatic Programmer DRY Principle](https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/)
