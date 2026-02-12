# Detailed Project Workflow Diagram

```mermaid
graph TD
    %% User Interaction
    User[User] --> UI[Chainlit UI]
    UI --> LG[LangGraph Agent System]

    %% Data Ingestion Subgraph
    subgraph "Data Ingestion Phase"
        IG[Ingestion Scripts]
        IG --> GH[GitHub Ingestor<br/>ingestion/github_ingestor.py]
        IG --> MD[Local MD Ingestor<br/>ingestion/local_md_ingestor.py]
        IG --> WEB[Web Ingestor<br/>ingestion/web_ingestor.py]

        GH --> GHDB[(GitHub DB<br/>github.db)]
        MD --> CMDB[(Comms DB<br/>planetix_comms.db)]
        WEB --> CMDB
    end

    %% Agent System Subgraph
    subgraph "LangGraph Agent System"
        LG --> SUP[Supervisor<br/>Routes queries]
        SUP -->|GitHub queries| GHA[GitHub Agent<br/>github_agent_call]
        SUP -->|Comms queries| CMA[Comms Agent<br/>comms_agent_call]

        GHA --> GHDEC[Decision: Tool needed?]
        CMA --> CMDEC[Decision: Tool needed?]

        GHDEC -->|Yes| GHTOOL[GitHub Tools<br/>retrieve_github_info<br/>list_tracked_repositories<br/>read_github_file]
        CMDEC -->|Yes| CMTOOL[Comms Tools<br/>retrieve_comms_info<br/>retrieve_slack_history]

        GHTOOL --> GHRET[Hybrid Retrieval<br/>Dense + BM25 + Reranking]
        CMTOOL --> CMRET[Hybrid Retrieval<br/>Dense + BM25 + Reranking]

        GHRET --> GHDB
        CMRET --> CMDB

        GHRET --> GHA
        CMRET --> CMA

        GHDEC -->|No| FINAL[Final Answer]
        CMDEC -->|No| FINAL

        GHA --> SUP
        CMA --> SUP
        FINAL --> SUP
    end

    %% UI Streaming
    LG --> UI
    UI --> User

    %% Optional Slack Integration
    subgraph "Optional Slack Bot"
        SLACK[Slack Server<br/>src/slack_server.py] --> LG
    end

    %% Configuration
    CONFIG[Configuration<br/>config/]
    CONFIG --> IG
    CONFIG --> LG

    %% Logging
    LOGS[Logs<br/>logs/agent.log<br/>logs/conversation_history.log]
    LG --> LOGS
    UI --> LOGS

    %% Styling
    classDef ingestion fill:#e1f5fe
    classDef agent fill:#f3e5f5
    classDef ui fill:#e8f5e8
    classDef db fill:#fff3e0
    classDef config fill:#fafafa

    class IG,GH,MD,WEB ingestion
    class SUP,GHA,CMA,GHDEC,CMDEC,GHTOOL,CMTOOL,GHRET,CMRET agent
    class UI ui
    class GHDB,CMDB db
    class CONFIG config