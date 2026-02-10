# Query Processing Flow Diagram

```mermaid
flowchart TD
    A[User Submits Query] --> B[Chainlit UI Receives Message]
    B --> C[Input Validation & Sanitization]
    C --> D[LangGraph Stream Events Start]

    D --> E[Supervisor Agent: Parse & Route Query]
    E --> F{Query Type?}
    F -->|GitHub| G[GitHub Agent]
    F -->|Comms| H[Comms Agent]
    F -->|Ambiguous| I[End: Ambiguous Response]

    G --> J[GitHub Agent: Load System Message]
    H --> K[Comms Agent: Load System Message]

    J --> L[Agent LLM Call with Context]
    K --> L

    L --> M[LLM Reasoning & Analysis]
    M --> N{Safety Check Passed?}
    N -->|No| O[End: Safety Violation Response]
    N -->|Yes| P{Knowledge Retrieval Needed?}

    P -->|Yes| Q[Tool Selection & Call]
    Q --> R[Tool Execution]
    R --> S[Observation Generation]
    S --> T[Add Observation to Context]
    T --> M

    P -->|No| U[Content Generation]
    U --> V[Response Formatting]
    V --> W[Streaming to UI]
    W --> X[User Presentation]
    X --> Y[Conversation Logging]
    Y --> Z[End]

    O --> Y
    I --> Y