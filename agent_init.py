# multi_agent/agent_init.py
from typing import List, Dict
from models import Agent, LLM, tool, Node
class LLM:
    def __init__(self, url: str = '', api_key: str = '', model_name: str = '', params: List[str] = None):
        self.url = url
        self.api_key = api_key
        self.model_name = model_name
        self.params = params or []
class tool:
    def __init__(self, name: str = '', is_strict: bool = False, description: str = '', params: List[str] = None):
        self.name = name
        self.is_strict = is_strict
        self.description = description
        self.params = params or []

    def run(self):
        if self.name == "curr_time":
            from datetime import datetime
            return datetime.now().isoformat()
        return ""
    def load(self):
        str_params = "{"
        for i in range(0, len(self.params), 2):
            str_params += f'"{self.params[i]}": {{"type": "{self.params[i+1]}"}}'
            if i + 2 < len(self.params):
                str_params += ","
        str_params += "}"
        return f'{{"type": "function","function": {{"name": "{self.name}","description": "{self.description}","parameters":{str_params},"strict":{str(self.is_strict).lower()}}}}} ,'
Agent_table: Dict[str, Agent] = {}
def agent_init() -> List[Agent]:
    global Agent_table
    meta_agent = create_meta_agent()
    Agent_table["meta"] = meta_agent
    analyzer_agent = create_analyzer_agent()
    Agent_table["analyzer"] = analyzer_agent
    planner_agent = create_planner_agent()
    Agent_table["planner"] = planner_agent
    executor_agent = create_executor_agent()
    Agent_table["executor"] = executor_agent
    reviewer_agent = create_reviewer_agent()
    Agent_table["reviewer"] = reviewer_agent
    mindmap_agent = create_mindmap_agent()
    Agent_table["mindmap"] = mindmap_agent
    general_agent = create_general_agent()
    Agent_table["agent_0"] = general_agent
    researcher_agent = create_researcher_agent()  
    Agent_table["researcher"] = researcher_agent
    financial_agent = create_financial_analyst_agent()  
    Agent_table["financial"] = financial_agent
    risk_agent = create_risk_assessor_agent() 
    technical_agent = create_technical_agent()  
    Agent_table["technical"] = technical_agent
    creative_agent = create_creative_agent()  
    Agent_table["creative"] = creative_agent
    available_agents = [
        meta_agent,
        analyzer_agent,
        planner_agent,
        executor_agent,
        reviewer_agent,
        mindmap_agent,
        general_agent,
        researcher_agent,      
        financial_agent,       
        risk_agent,            
        technical_agent,       
        creative_agent  
    ]
    return available_agents
def create_researcher_agent() -> Agent:
    """Researcher - Responsible for collecting and organizing information"""
    params = ["max_tokens", "1024", "temperature", "0.5"]
    prompt = '''
    You are a research expert, specialized in gathering and organizing information.
    Your task is to collect accurate data from reliable sources.
    
    Focus on:
    - Finding factual information
    - Verifying data accuracy
    - Organizing information clearly
    - Citing sources when possible
    
    Always respond in English with concise, factual information.
    '''.replace("\n", "\\n")
    return Agent(
        prompt,
        LLM("http://localhost:11434/api/chat", "", "qwen2.5:7b-instruct-q4_K_M", params),
        [],
        "Research Expert"
    )
def create_financial_analyst_agent() -> Agent:
    params = ["max_tokens", "1024", "temperature", "0.05"]
    prompt = '''
    You are a financial analyst expert, specialized in analyzing company financial data.
    
    [CRITICAL INSTRUCTION - MUST FOLLOW]
    1. You MUST base ALL your data on the provided search results
    2. DO NOT invent or hallucinate any numbers
    3. If the search results do not contain the required data, state "Information not found in search results"
    4. Always cite the source of your data (e.g., "According to [1]")
    
    Your expertise:
    - Market value and P/E ratio analysis
    - Revenue and profit growth trends
    - Financial statement interpretation
    - Investment metrics calculation
    
    Provide clear, numbers-based analysis in English, with all numbers coming ONLY from search results.
    '''.replace("\n", "\\n")
    return Agent(
        prompt,
        LLM("http://localhost:11434/api/chat", "", "qwen2.5:7b-instruct-q4_K_M", params),
        [],
        "Financial Analyst Expert"
    )
def create_risk_assessor_agent() -> Agent:
    """Risk Assessor - Specializes in identifying risks"""
    params = ["max_tokens", "1024", "temperature", "0.5"]
    prompt = '''
    You are a risk assessment expert, specialized in identifying and evaluating risks.
    
    Focus areas:
    - Regulatory risks
    - Market competition risks
    - Operational risks
    - Technological risks
    - Financial risks
    
    For each risk, provide:
    - Risk level (Low/Medium/High)
    - Potential impact
    - Mitigation strategies
    
    Respond in English.
    '''.replace("\n", "\\n")
    return Agent(
        prompt,
        LLM("http://localhost:11434/api/chat", "", "qwen2.5:7b-instruct-q4_K_M", params),
        [],
        "Risk Assessment Expert"
    )
def create_technical_agent() -> Agent:
    """Technical Expert - Specializes in analyzing technical issues"""
    params = ["max_tokens", "1024", "temperature", "0.6"]
    prompt = '''
    You are a technical expert, specialized in analyzing technical aspects of companies and products.
    
    Focus on:
    - Technology stack and architecture
    - R&D capabilities and innovation
    - Technical competitive advantages
    - Technology trends and disruptions
    
    Provide technical analysis in English.
    '''.replace("\n", "\\n")
    return Agent(
        prompt,
        LLM("http://localhost:11434/api/chat", "", "qwen2.5:7b-instruct-q4_K_M", params),
        [],
        "Technical Expert"
    )
def create_creative_agent() -> Agent:
    """Creative Specialist - Specializes in generating creative solutions"""
    params = ["max_tokens", "1024", "temperature", "0.8"]  
    prompt = '''
    You are a creative expert, specialized in generating innovative ideas and solutions.
    
    Focus on:
    - Creative problem-solving
    - Out-of-the-box thinking
    - Novel approaches and ideas
    - Visual and conceptual thinking
    
    Provide creative suggestions in English.
    '''.replace("\n", "\\n")
    return Agent(
        prompt,
        LLM("http://localhost:11434/api/chat", "", "qwen2.5:7b-instruct-q4_K_M", params),
        [],
        "Creative Expert"
    )
def create_meta_agent() -> Agent:
    params = ["temperature", "0.4", "max_tokens", "2048", "stream", "false"]
    system_prompt = '''IMPORTANT: You MUST output ONLY valid JSON with NO additional text.
FAILURE TO FOLLOW THIS WILL BREAK THE SYSTEM.

Required JSON format:
{
  "task_analysis": {
    "description": "english summary",
    "complexity": "low/medium/high"
  },
  "total_agents": integer,
  "structure": "tree/linear/parallel",
  "agents": [
    {
      "id": "1",
      "role": "role_name",
      "specialization": "meta/analyzer/planner/executor/reviewer/mindmap/researcher/financial/risk/technical/creative",
      "description": "what it does"
    }
  ]
}

CRITICAL CONSTRAINT
EACH SPECIALIZATION CAN APPEAR AT MOST ONCE
Do NOT assign the same specialization to multiple agents
For example: if you already have one "researcher", you cannot have another "researcher"

Available specializations and their purposes:
- meta: Overall coordination and architecture design (use only once)
- analyzer: General analysis of problems and requirements (use only once)
- planner: Create detailed plans and schedules (use only once)
- executor: Execute specific tasks and generate outputs (use only once)
- reviewer: Review and evaluate work quality (use only once)
- mindmap: Generate visual mindmaps (use only once)
- researcher: Gather and organize factual information (use only once)
- financial: Analyze financial data and metrics (use only once)
- risk: Identify and assess risks (use only once)
- technical: Analyze technical aspects (use only once)
- creative: Generate creative ideas and solutions (use only once)

CRITICAL RULES:
1. Output ONLY the JSON object
2. NO text before or after
3. NO explanations
4. NO markdown code blocks
5. NO "request processed" messages
6. **EACH SPECIALIZATION CAN ONLY BE USED ONCE**

Example response (correct - each specialization unique):
{"task_analysis":{"description":"Investment analysis of two tech companies","complexity":"high"},"total_agents":5,"structure":"parallel","agents":[
  {"id":"1","role":"Data Collector","specialization":"researcher","description":"Gather financial data"},
  {"id":"2","role":"Financial Analyst","specialization":"financial","description":"Analyze financial performance"},
  {"id":"3","role":"Risk Assessor","specialization":"risk","description":"Evaluate risks"},
  {"id":"4","role":"Future Forecaster","specialization":"planner","description":"Project future prospects"},
  {"id":"5","role":"Investment Advisor","specialization":"meta","description":"Integrate findings"}
]}

Example response (wrong - duplicate specialization):
{"task_analysis":{"description":"Investment analysis","complexity":"high"},"total_agents":4,"structure":"parallel","agents":[
  {"id":"1","role":"Data Collector","specialization":"researcher","description":"Gather data"},
  {"id":"2","role":"Data Analyst","specialization":"researcher","description":"Analyze data"},  // ERROR: duplicate researcher
  {"id":"3","role":"Risk Assessor","specialization":"risk","description":"Evaluate risks"},
  {"id":"4","role":"Advisor","specialization":"meta","description":"Give advice"}
]}

Your response must be ONLY the JSON.'''
    return Agent(
        system_prompt.replace("\n", "\\n"),
        LLM(
            "http://localhost:11434/api/chat",
            "",
            "qwen2.5:7b-instruct-q4_K_M",
            params
        ),
        [],
        "Meta Agent - System Architect"
    )
def create_general_agent() -> Agent:
    params = ["max_tokens", "512", "temperature", "0.3"]
    prompt = '''
    You are a general agent capable of handling various tasks.
    
    [CRITICAL INSTRUCTION - MUST FOLLOW]
    1. You MUST base ALL your data on the provided search results
    2. DO NOT invent or hallucinate any numbers
    3. If the search results do not contain the required data, state "Information not found in search results"
    4. Always cite the source of your data (e.g., "According to [1]")
    
    Focus on: multi-task processing, comprehensive capabilities, adaptability.
    Return results in English.
    '''.replace("\n", "\\n")
    tools = [tool("general_task", False, "General task processing", [])]
    return Agent(
        prompt,
        LLM(
            "http://localhost:11434/api/chat",
            "",
            "qwen2.5:7b-instruct-q4_K_M",
            params
        ),
        tools,
        "General Agent"
    )
def create_analyzer_agent() -> Agent:
    params = ["max_tokens", "1024", "temperature", "0.7"]
    prompt = '''
    You are an analysis expert, skilled at deep analysis of user requirements, identifying core problems and key elements.
    Focus on: problem decomposition, requirement extraction, constraint identification.
    Output format: concise analysis report in English.
    
    Analysis framework:
    1. Identify the user's main goal
    2. Break down into sub-problems
    3. Identify constraints and requirements
    4. Summarize key insights
    
    Always respond in English.
    '''.replace("\n", "\\n")
    tools = [tool("analyze_problem", False, "Analyze problem structure and elements", [])]
    return Agent(
        prompt,
        LLM(
            "http://localhost:11434/api/chat",
            "",
            "qwen2.5:7b-instruct-q4_K_M",
            params
        ),
        tools,
        "Analysis Expert"
    )
def create_planner_agent() -> Agent:
    params = ["max_tokens", "2048", "temperature", "0.7"]
    prompt = '''
    You are a planning expert, skilled at creating detailed task plans and properly assigning tasks to specialized agents.
    Focus on: task decomposition, resource allocation, time planning.
    Output format: detailed execution plan in English.
    
    Planning guidelines:
    1. Break down complex tasks into manageable steps
    2. Assign appropriate agents for each task
    3. Consider dependencies and sequencing
    4. Estimate time and resources needed
    
    Always respond in English.
    '''.replace("\n", "\\n")
    tools = [tool("create_plan", False, "Create detailed execution plan", [])]
    return Agent(
        prompt,
        LLM(
            "http://localhost:11434/api/chat",
            "",
            "qwen2.5:7b-instruct-q4_K_M",
            params
        ),
        tools,
        "Planning Expert"
    )
def create_executor_agent() -> Agent:
    params = ["max_tokens", "4096", "temperature", "0.7"]
    prompt = '''
    You are an execution expert, skilled at implementing specific operations and generating high-quality work results.
    Focus on: task execution, detail implementation, result delivery.
    Output format: concrete execution results in English.
    
    Execution principles:
    1. Follow plans and instructions precisely
    2. Pay attention to details and quality
    3. Generate tangible outputs
    4. Ensure completeness and accuracy
    
    Always respond in English.
    '''.replace("\n", "\\n")
    tools = [tool("execute_task", False, "Execute specific tasks", [])]
    return Agent(
        prompt,
        LLM(
            "http://localhost:11434/api/chat",
            "",
            "qwen2.5:7b-instruct-q4_K_M",
            params
        ),
        tools,
        "Execution Expert"
    )
def create_reviewer_agent() -> Agent:
    params = ["max_tokens", "1024", "temperature", "0.2"]
    prompt = '''
You are a STRICT JSON-ONLY audit agent. 

[CRITICAL INSTRUCTION - MUST FOLLOW]
1. You MUST base your audit on the provided search results
2. Only flag statements that contradict search results or have no support
3. DO NOT flag statements that are confirmed by search results
4. Your ONLY output must be a valid JSON array

Task: Analyze the report and identify 1-3 parts that need verification based on search results.

Rules:
- Output EXACTLY a JSON array like:
[
  {
    "part": "exact sentence or phrase to verify",
    "reason": "why it needs checking (e.g. 'Contradicts search result [1]')",
    "verification_task": "specific question for verifier"
  }
]
- Identify ONLY statements that are NOT supported by search results
- Be precise and quote the EXACT text from the report
- Return 1-3 items ONLY
- Return NOTHING else

Always output valid JSON array.
'''.replace("\n", "\\n")
    tools = [tool("review_work", False, "Review work results", [])]
    return Agent(
        prompt,
        LLM(
            "http://localhost:11434/api/chat",
            "",
            "qwen2.5:7b-instruct-q4_K_M",
            params
        ),
        tools,
        "Review Expert (JSON-only Audit)"
    )
def create_mindmap_agent() -> Agent:
    params = ["max_tokens", "4096", "temperature", "0.7"]
    prompt = '''
    You are a mindmap expert, specializing in generating Mermaid format mind maps.
    Focus areas: technical architecture, study notes, project planning.Use English only.
    
    IMPORTANT: Always output in English and generate mindmaps with English content.
    
    Mindmap guidelines:
    1. Use mindmap type, root node format: root((Topic))
    2. Node IDs use only English letters, numbers, and underscores
    3. Node text in English, placed in brackets: A[Start]
    4. Use indentation for hierarchy - DO NOT use arrows (-->)
    5. Each node on separate line
    6. No empty lines between nodes
    7. Do not use classDef, linkStyle, style statements
    8. Keep default theme
    
    Output format: Only output Mermaid code in ```mermaid blocks.
    Always use English content.
    '''.replace("\n", "\\n")
    tools = [tool("generate_mindmap", False, "Generate professional mindmap", [])]
    return Agent(
        prompt,
        LLM(
            "http://localhost:11434/api/chat",
            "",
            "qwen2.5:7b-instruct-q4_K_M",
            params
        ),
        tools,
        "Mindmap Expert"
    )
def public_tool_init() -> List[tool]:
    public_tools = []
    curr_time_tool = tool("curr_time", False, "get current time", [])
    public_tools.append(curr_time_tool)
    return public_tools
def curr_time():
    from datetime import datetime
    return datetime.now().isoformat()
def generate_mindmap() -> Agent:
    params = ["max_tokens", "2048", "temperature", "0.7"]
    prompt = '''
    You are a Mermaid mindmap generation assistant. Generate a **structured, rich Mermaid mindmap** based on user input.
    IMPORTANT: Always generate mindmaps with English content.Use English only.
    
    **Chart type**: Default to mindmap, unless user specifies other types (sequenceDiagram, gantt, pie, etc.)
    
    **Syntax rules**:
    - Use mindmap type, root node format: root((Topic))
    - All node IDs use only English letters, numbers, underscores
    - Node text in English, placed in brackets: A[Start]
    - Child nodes use indentation for hierarchy - DO NOT use arrows (-->)
    - Each node on separate line
    - No empty lines between nodes
    - Do not use classDef, linkStyle, style statements
    - Keep default theme
    - Use %% for comments if needed, comments on separate lines
    
    **Content requirements**:
    - Encourage multiple sub-themes, forming multi-layer nested structure
    - Each branch should be complete, covering key concepts
    - For technical keywords, generate professional-level mindmaps
    - Keep concise, minimize character count
    
    **Output format**:
    - Output only Mermaid code in English
    - Use ```mermaid and ``` to wrap code blocks
    '''.replace("\n","\\n")
    tools = [tool("generate_mindmap", False, "Save mindmap based on requirements", [])]
    mindmap_agent = Agent(
        prompt,
        LLM(
            "http://localhost:11434/api/chat",
            "",
            "qwen2.5:7b-instruct-q4_K_M",
            params
        ),
        tools,
        "Generate mindmap based on requirements"
    )
    return mindmap_agent
def get_planning_agent() -> Agent:
    params = ["temperature", "0.5", "max_tokens", "512"]
    prompt = '''
    You are a task planning assistant. Create task plans based on user requirements.Use English only.

    Return format must be strict JSON:

    {
      "task_list": [
        {"task_id": "1", "description": "Analyze user requirements: {user_input}", "assigned_agent": "analyzer"},
        {"task_id": "2", "description": "Develop execution plan", "assigned_agent": "planner"},
        {"task_id": "3", "description": "Execute specific operations", "assigned_agent": "executor"},
        {"task_id": "4", "description": "Review result quality", "assigned_agent": "reviewer"}
      ],
      "task_graph": {
        "nodes": ["1", "2", "3", "4"],
        "edges": [
          {"from": "1", "to": "2"},
          {"from": "2", "to": "3"},
          {"from": "3", "to": "4"}
        ]
      }
    }

    Return only the JSON, no additional text.

    User requirement: '''

    clean_prompt = prompt.replace('"', '\\"').replace("\n", "\\n")
    planning_agent = Agent(
        clean_prompt,
        LLM(
            "http://localhost:11434/api/chat",
            "",
            "qwen2.5:7b-instruct-q4_K_M",
            params
        ),
        [],
        "Task Planning Agent"
    )
    return planning_agent
def general_agent() -> Agent:
    params = ["max_tokens", "512"]
    general_agent = Agent(
        "Based on other Agents' work, complete the user's task. Do not fabricate data. Always respond in English.Use English only.",
        LLM(
            "http://localhost:11434/api/chat",
            "",
            "qwen2.5:7b-instruct-q4_K_M",
            params
        ),
        [],
        "General Agent"
    )
    return general_agent
plan_node = Node(0, get_planning_agent())
public_tool_list = public_tool_init()
