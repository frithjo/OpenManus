# OpenManus Project Reference Guide (Pin and Lock)

This document serves as a reference guide for the OpenManus project, outlining its scope, structure, relationships, dependencies, and modifications made using the "pin and lock" approach.

## Project Scope

OpenManus is an agent-based system designed to interact with users and perform tasks using a variety of tools. The core functionalities include:

-   **Natural Language Understanding:** Processing user input and understanding their intent.
-   **Tool Selection:** Choosing the appropriate tools to accomplish tasks.
-   **Tool Execution:** Interacting with external services and executing tools.
-   **Memory Management:** Maintaining conversation history and context.
-   **Planning:** Creating and managing plans for complex tasks.
-   **Web browsing**: Interacting with a web browser.
-   **Python execution**: Executing Python code.
-   **Web search**: Performing web searches.
-   **File saving**: Saving files.
-   **Terminal**: Executing terminal commands.

## Dependency Tree

```mermaid
graph TD
    subgraph Agents
        A[AgentBase] --> B(ToolCallAgent);
        A --> C(PlanningAgent);
        B --> D(Manus);
    end
    subgraph Tools
        E[BaseTool] --> F(BrowserUseTool);
        E --> G(PythonExecute);
        E --> H(WebSearch);
        E --> I(PlanningTool);
        E --> J(FileSaver);
        E --> K(Terminate);
        E --> L(Terminal);
        M(SerperAPIWrapper)
        H --> M
        N(ToolCollection)
        N --> F
        N --> G
        N --> H
        N --> I
        N --> J
        N --> K
        N --> L
    end
    subgraph LLM
        O[LLM]
    end
    subgraph Memory
        P[BaseMemory] --> Q(SimpleMemory);
        R(Schema)
        Q --> R
    end
    subgraph Prompts
        S[PromptBase] --> T(MessagePrompt);
        S --> U(PromptFormatter);
        V(ToolUsePrompt)
        W(PlanningPrompt)
    end
    subgraph Configuration
        X[Config]
    end
    subgraph Main
        Y[Main]
    end
    subgraph Other
        Z[Exceptions]
        AA[Logger]
    end
    B --> O
    C --> O
    D --> O
    F --> O
    G --> O
    H --> O
    I --> O
    J --> O
    K --> O
    L --> O
    M --> O
    N --> O
    B --> N
    C --> N
    D --> N
    Y --> D
    Y --> O
    Y --> X
    B --> R
    C --> R
    D --> R
    F --> R
    G --> R
    H --> R
    I --> R
    J --> R
    K --> R
    L --> R
    M --> R
    N --> R
    O --> R
    Q --> R
    T --> R
    U --> S
    V --> S
    W --> S
    B --> T
    C --> T
    D --> T
    Y --> AA
