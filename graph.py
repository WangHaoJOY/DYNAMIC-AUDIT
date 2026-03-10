# multi_agent/graph.py
from typing import List, Dict, Tuple
from dataclasses import dataclass
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from agent_init import (
    Agent_table, agent_init, Agent, LLM
)
from models import Agent, LLM, Node, Graph

@dataclass
class MetaArchitecture:
    plan: str = ""
    agent_count: int = 0
    structure_type: str = "linear"
    complexity_level: str = "medium"
class ParallelCollector:
    def __init__(self):
        self.results = []
        self.agents = []
        self.completed_count = 0
        print("ParallelCollector initialized")
    def add_result(self, agent_name: str, result: str):
        self.results.append(result)
        self.agents.append(agent_name)
        self.completed_count += 1
    def get_results(self) -> List[str]:
        return self.results
    def get_agents(self) -> List[str]:
        return self.agents
class workflow:
    def __init__(self):
        self.wf_graph = Graph()
        self.total_nodes = 0
        self.final_result = ""
        self.collaboration_context = {}
        self.debug_mode = False
        self.parallel_collector = ParallelCollector()
        self.print_lock = threading.Lock()
        self.ensure_agents_initialized()
    def safe_print(self, message: str):
        with self.print_lock:
            print(message)
    def work(self, user_input: str):
        print("·································")
        print(f"Starting multi-agent collaboration: {user_input}")
        print("·································")
        try:
            print("\nPhase 1: Meta agent analyzing task and designing architecture")
            meta_plan = ""
            agent_count = 0
            if len(Agent_table) == 0:
                self.ensure_agents_initialized()
            meta_agent = Agent_table.get("meta")
            if meta_agent is None:
                print("Warning: Meta agent does not exist, using smart analysis")
                agent_count = self.determine_agent_count_by_input(user_input)
                meta_plan = self.generate_smart_plan(user_input, agent_count, "tree")
            else:
                print("Meta agent analyzing task...")
                forced_prompt = f"""You are the Meta Agent. Design a multi-agent architecture for the task below.

You MUST output ONLY a valid JSON object with NO other text.

The JSON must have this EXACT structure:
{{
  "task_analysis": {{
    "description": "Brief English summary of the task",
    "complexity": "low" or "medium" or "high"
  }},
  "total_agents": (integer between 2 and 5),
  "structure": "tree" or "linear" or "parallel",
  "agents": [
    {{
      "id": "1",
      "role": "role name in English",
      "specialization": "one of: meta/analyzer/planner/executor/reviewer/researcher/financial/risk/technical/creative",
      "description": "what this agent does in English"
    }}
  ]
}}

IMPORTANT:
- The field names MUST be exactly: "task_analysis", "total_agents", "structure", "agents"
- Inside each agent, the field names MUST be exactly: "id", "role", "specialization", "description"
- Do NOT use "team", "name", or any other field names
- Choose specializations based on what the task needs
- Each specialization can only be used once

Task: {user_input}

Return ONLY the JSON object:"""
                print("Calling meta agent to design structure...")
                response = meta_agent.send_msg2agent(forced_prompt)
                if "Request handled" in response or len(response.strip()) < 200 or "{" not in response:
                    print("Meta agent output invalid! Forcing fallback to 4 agent mode")
                    agent_count = 4
                    meta_plan = self.generate_smart_plan(user_input, agent_count, "tree")
                else:
                    meta_design = self.parse_meta_tree_design(response, user_input)
                    meta_plan = meta_design.plan
                    agent_count = meta_design.agent_count
                    print(f"Meta agent design completed: {agent_count} agents, structure: {meta_design.structure_type}")
            print("\nPhase 2: Executing collaboration based on meta agent design")
            if not meta_plan:
                print("Meta agent design failed, using standard process")
                meta_plan = self.get_default_plan(user_input)
                agent_count = 4
            self.wf_graph.setNumber(agent_count)            
            plan_nodes = self.extract_agent_nodes_from_meta_plan(meta_plan)
            self.create_meta_agent_nodes(plan_nodes)            
            if len(self.wf_graph.nodes) == 0:
                print("Error: No executable agent nodes")
                self.final_result = "Error: No executable agent nodes"
                return            
            print("\nExecution statistics:")
            print(f"  - Meta agent design: {agent_count} agents")
            print(f"  - Actual nodes created: {len(self.wf_graph.nodes)}")            
            print("  - Agents used:")
            for j, node in enumerate(self.wf_graph.nodes):
                print(f"    {j+1}. {node.description}")            
            print("\nPhase 3: Executing collaboration")
            self.execute_tree_collaboration(user_input)            
        except Exception as e:
            print(f"\nWorkflow execution exception: {e}")
            import traceback
            traceback.print_exc()
            self.final_result = f"Exception during execution: {e}"        
        print("\n" + "···································")
        print("Processing complete")
        print("···································")
        try:
            with open("output.txt", "w", encoding="utf-8") as f:
                f.write(self.final_result)
        except Exception as e:
            print(f"Failed to save results: {e}")            
    def parse_meta_tree_design(self, response: str, user_input: str) -> MetaArchitecture:
        print("Starting to parse meta agent response...")    
        import re
        import json    
        try:
            agents_pattern = r'"agents"\s*:\s*\[(.*?)\]'
            agents_match = re.search(agents_pattern, response, re.DOTALL)        
            if agents_match:
                agents_str = agents_match.group(1)
                agents_str = re.sub(r'\s+', ' ', agents_str)
                agents_str = agents_str.replace('*', '')
                agents_str = re.sub(r'(\d+)\s*\*\s*1e9', r'\1000000000', agents_str)            
                try:
                    full_json = '{' + f'"agents":[{agents_str}]' + '}'
                    data = json.loads(full_json)
                    agents = data.get("agents", [])                
                    if agents:
                        total_agents = len(agents)
                        structure_match = re.search(r'"structure"\s*:\s*"([^"]+)"', response)
                        structure = structure_match.group(1) if structure_match else "tree"
                        complexity_match = re.search(r'"complexity"\s*:\s*"([^"]+)"', response)
                        complexity = complexity_match.group(1) if complexity_match else "medium"
                        print(f"Successfully extracted agents array: {total_agents} agents")
                        meta_json = {"agents": agents}
                        plan = self.generate_tree_plan_from_meta_design(meta_json, user_input)
                        return MetaArchitecture(plan, total_agents, structure, complexity)
                except Exception as e:
                    print(f"Failed to parse agents array: {e}")
        except Exception as e:
            print(f"Failed to extract agents array: {e}")
        try:
            agent_match = re.search(r'"total_agents"\s*:\s*(\d+)', response)
            total_agents = int(agent_match.group(1)) if agent_match else 4
            structure_match = re.search(r'"structure"\s*:\s*"([^"]+)"', response)
            structure = structure_match.group(1) if structure_match else "tree"
            complexity_match = re.search(r'"complexity"\s*:\s*"([^"]+)"', response)
            complexity = complexity_match.group(1) if complexity_match else "medium"
            print(f"Using regex extracted total_agents: {total_agents}, structure={structure}, complexity={complexity}")
            plan = self.generate_smart_plan(user_input, total_agents, structure)
            return MetaArchitecture(plan, total_agents, structure, complexity)
        except Exception as e:
            print(f"Regex extraction failed: {e}")
            count = self.determine_agent_count_by_input(user_input)
            plan = self.generate_smart_plan(user_input, count, "tree")
            return MetaArchitecture(plan, count, "tree", "medium")
    def generate_tree_plan_from_meta_design(self, meta_json: Dict, user_input: str) -> str:
        try:
            agents_array = meta_json.get("agents", [])
            task_list = []
            nodes_list = []
            edges_list = []
            agent_count = len(agents_array) if agents_array else 4
            for i in range(agent_count):
                agent_id = ""
                agent_type = "analyzer"
                agent_role = ""
                specialization = ""
                if len(agents_array) > i:
                    agent_info = agents_array[i]
                    agent_id = agent_info.get("id", str(i+1))
                    specialization = agent_info.get("specialization", "")
                    agent_type = self.map_agent_specialization(specialization)
                    agent_role = agent_info.get("role", "")
                if not agent_id:
                    agent_id = str(i+1)
                description = agent_role or f"{specialization}: {user_input}" or self.get_tree_agent_description(agent_type, user_input, i)
                description = description.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                task_item = {
                    "task_id": agent_id,
                    "description": description,
                    "assigned_agent": agent_type
                }
                task_list.append(task_item)
                nodes_list.append(agent_id)
                if i > 0:
                    parent_idx = (i - 1) // 2
                    parent_id = str(parent_idx + 1)
                    edges_list.append({"from": parent_id, "to": agent_id})            
            plan_obj = {
                "task_list": task_list,
                "task_graph": {
                    "nodes": nodes_list,
                    "edges": edges_list
                }
            }
            return json.dumps(plan_obj, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to generate plan from meta design: {e}")
            return self.generate_smart_plan(user_input, 4, "tree")
    def get_tree_agent_description(self, agent_type: str, user_input: str, index: int) -> str:
        descriptions = {
            "meta": f"Meta agent: Coordinate solution for {user_input}",
            "analyzer": f"Analysis expert: Analyze requirements and constraints for {user_input}",
            "planner": f"Planning expert: Develop implementation plan for {user_input}",
            "executor": f"Execution expert: Implement specific solution for {user_input}",
            "reviewer": f"Review expert: Evaluate solution quality for {user_input}",
            "mindmap": f"Mindmap expert: Generate visual mindmap for {user_input}",
            "agent_0": f"General agent: Handle related tasks for {user_input}"
        }
        return descriptions.get(agent_type, f"{agent_type} handling task {index + 1} for {user_input}")
    def determine_agent_count_by_input(self, user_input: str) -> int:
        input_lower = user_input.lower()
        length = len(user_input)
        if length < 30:
            return 2
        elif length < 100:
            return 3
        elif length < 200:
            return 4
        elif length < 500:
            return 5
        else:
            return 6
    def generate_smart_plan(self, user_input: str, agent_count: int, structure_type: str) -> str:
        agent_types = ["analyzer"]
        if agent_count >= 2:
            agent_types.append("planner")
        if agent_count >= 3:
            agent_types.append("executor")
        if agent_count >= 4:
            agent_types.append("reviewer")
        expert_agents = ["technical", "creative", "research", "agent_0"]
        expert_idx = 0
        while len(agent_types) < agent_count and expert_idx < len(expert_agents):
            agent_types.append(expert_agents[expert_idx])
            expert_idx += 1
        plan = '{"task_list":['
        nodes_list = []
        edges_list = []
        for i in range(agent_count):
            agent_id = str(i+1)
            agent_type = agent_types[i]
            description = self.get_agent_task_description(agent_type, user_input, i, agent_count)
            plan += f'{{"task_id":"{agent_id}","description":"{description}","assigned_agent":"{agent_type}"}}'
            nodes_list.append(f'"{agent_id}"')
            if structure_type == "tree" and i > 0:
                parent_idx = (i - 1) // 2
                parent_id = str(parent_idx + 1)
                edges_list.append(f'{{"from":"{parent_id}","to":"{agent_id}"}}')
            elif i > 0:
                prev_id = str(i)
                edges_list.append(f'{{"from":"{prev_id}","to":"{agent_id}"}}')
            if i < agent_count - 1:
                plan += ","
        plan += '],"task_graph":{"nodes":[' + ",".join(nodes_list) + '],"edges":[' + ",".join(edges_list) + ']}}'
        return plan
    def get_agent_task_description(self, agent_type: str, user_input: str, index: int, total: int) -> str:
        descriptions = {
            "analyzer": f"Analyze requirements: {user_input}",
            "planner": "Create detailed implementation plan",
            "executor": "Execute specific implementation",
            "reviewer": "Review quality and provide feedback",
            "mindmap": "Generate visual mindmap of solution",
            "technical": "Technical analysis and architecture design",
            "creative": "Creative idea generation",
            "research": "Research and data analysis",
            "meta": "Coordinate multi-agent collaboration",
            "agent_0": "General task execution"
        }
        return descriptions.get(agent_type, "Subtask " + str(index + 1) + " execution")
    def extract_agent_nodes_from_meta_plan(self, plan: str) -> List[str]:
        try:
            import re
            cleaned_plan = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', plan)
            plan_json = json.loads(cleaned_plan)
            task_list = plan_json["task_list"]
            nodes = []
            for i, task in enumerate(task_list):
                nodes.append(task["task_id"])
                nodes.append(task["description"])
                nodes.append(task["assigned_agent"])
            return nodes
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            return []
        except Exception as e:
            print(f"Failed to extract nodes from meta plan: {e}")
            return []
    def create_meta_agent_nodes(self, plan_nodes: List[str]):
        if not plan_nodes:
            self.create_default_agent_nodes()
            return
        i = 0
        while i < len(plan_nodes) // 3:
            base_idx = i * 3
            if base_idx + 2 < len(plan_nodes):
                task_id = plan_nodes[base_idx]
                description = plan_nodes[base_idx + 1]
                agent_name = plan_nodes[base_idx + 2]
                mapped_agent_name = self.map_agent_specialization(agent_name)
                agent = Agent_table.get(mapped_agent_name)
                if agent:
                    n = Node(int(task_id), agent)
                    n.description = description
                    self.wf_graph.nodes.append(n)
                    print(f"Created agent: ID={task_id}, role={description}, type={mapped_agent_name}")
                else:
                    self.create_fallback_agent_node(task_id, description, agent_name)
            i += 1
    def map_agent_specialization(self, specialization: str) -> str:
        """Map meta agent design specialization to actual Agent type"""
        specialization_lower = specialization.lower()
        if "meta" in specialization_lower:
            return "meta"
        if any(word in specialization_lower for word in ["financial", "finance"]):
            return "financial"
        if any(word in specialization_lower for word in ["market", "sales", "research"]):
            return "researcher"
        if any(word in specialization_lower for word in ["risk", "policy", "supply chain", "valuation"]):
            return "risk"
        if any(word in specialization_lower for word in ["technical", "technology", "battery", "autonomous", "cockpit", "moat"]):
            return "technical"
        if any(word in specialization_lower for word in ["future", "outlook", "driver", "challenge"]):
            return "creative"
        if any(word in specialization_lower for word in ["analyzer", "analysis", "analyze"]):
            return "analyzer"
        if any(word in specialization_lower for word in ["planner", "planning", "plan"]):
            return "planner"
        if any(word in specialization_lower for word in ["executor", "execution", "implement"]):
            return "executor"
        if any(word in specialization_lower for word in ["reviewer", "review", "quality"]):
            return "reviewer"
        if any(word in specialization_lower for word in ["mindmap", "visual", "graph", "map"]):
            return "mindmap"
        mapping = {
            "meta": "meta",
            "analyzer": "analyzer",
            "planner": "planner",
            "executor": "executor",
            "reviewer": "reviewer",
            "mindmap": "mindmap",
            "agent_0": "agent_0",
            "research": "researcher",
            "researcher": "researcher",
            "financial": "financial",
            "finance": "financial",
            "risk": "risk",
            "risk_assessor": "risk",
            "technical": "technical",
            "tech": "technical",
            "creative": "creative",
            "creativity": "creative"
        }
        return mapping.get(specialization, "analyzer")
    def create_fallback_agent_node(self, task_id: str, description: str, requested_agent: str):
        fallback_agents = ["analyzer", "planner", "executor", "agent_0"]
        
        for agent_name in fallback_agents:
            agent = Agent_table.get(agent_name)
            if agent:
                n = Node(int(task_id), agent)
                n.description = f"{description} (fallback: {agent_name})"
                self.wf_graph.nodes.append(n)
                return
    def create_default_agent_nodes(self):
        default_agents = ["analyzer", "planner", "executor", "reviewer"]
        for i, agent_name in enumerate(default_agents):
            agent = Agent_table.get(agent_name)
            if agent:
                n = Node(i+1, agent)
                n.description = f"{agent_name} standard task"
                self.wf_graph.nodes.append(n)
    def execute_tree_collaboration(self, user_input: str):
        print("\n··················· Starting Collaboration ···················")
        results = {}
        collaboration_chain = []
        total_agents = len(self.wf_graph.nodes)
        print("\nPhase 1: Root node analysis")
        root_analysis = ""
        if total_agents > 0:
            root_node = self.wf_graph.nodes[0]
            root_agent_name = self.get_agent_name(root_node.goal_agent)
            print(f"Root node: {root_agent_name}")
            root_context = f"As the root node of the collaboration system, please analyze the entire task:\n\n{user_input}\n\n"
            root_context += "Provide a guiding framework for subsequent subtasks."
            try:
                root_analysis = root_node.send_msg(root_context)
                root_analysis = self.safe_text(root_analysis)
                self.add_to_results(results, root_agent_name, root_analysis)
                collaboration_chain.append(root_agent_name)
                print("Root node analysis complete")
            except Exception as e:
                print(f"Root node execution exception: {e}")
                root_analysis = "Root node analysis failed"
        print("\nPhase 2: Parallel execution of subtasks")
        if total_agents <= 1:
            print("No subtasks to execute")
            valid_results = []
        else:
            parallel_tasks = []
            for i in range(1, total_agents):
                node = self.wf_graph.nodes[i]
                agent_name = self.get_agent_name(node.goal_agent)
                task_info = (agent_name, node, i, root_analysis, user_input)
                parallel_tasks.append(task_info)
                collaboration_chain.append(agent_name)
            print(f"Starting parallel execution of {len(parallel_tasks)} subtasks")
            with ThreadPoolExecutor(max_workers=min(3, len(parallel_tasks))) as executor:
                futures = []
                for task_info in parallel_tasks:
                    future = executor.submit(self.execute_parallel_task, task_info)
                    futures.append(future)
                for i, future in enumerate(futures):
                    try:
                        agent_name, result = future.result()
                        if agent_name and result:
                            self.add_to_results(results, agent_name, result)
                        print(f"Task {i+1}/{len(futures)} completed: {agent_name}")
                    except Exception as e:
                        print(f"Task execution failed: {e}")
            valid_results = []
            for task in parallel_tasks:
                agent_name = task[0]
                if agent_name in results and results[agent_name]:
                    result = results[agent_name][-1]
                    valid_results.append(result)
            print(f"Collected {len(valid_results)} valid results")
        print("\nPhase 3: Result integration")
        try:
            print("Using General Agent for final integration")
            search_section = ""
            if "[Web Search Results]" in user_input and "[User Question]" in user_input:
                parts = user_input.split("[User Question]")
                search_section = parts[0]
            integration_context = f"""FINAL INTEGRATION TASK
YOUR TASK:
Based on all the above information, provide a **concise, complete, professional** investment analysis report.
[IMPORTANT INSTRUCTIONS]
You must **strictly base your final report on the following [Web Search Results]**:
1. All data must come from search results, do not fabricate
2. If there are inconsistencies in search results, choose the most frequently occurring
3. Clearly label data sources in the report (cite search result numbers)
Requirements:
- Keep the length within 2000-3000 characters, highly summarized but information-rich, **avoid verbosity and repetition**, **must be between 2000-3000 characters**
- Clear structure: Use headings for sections
- Prioritize high-confidence facts
- Provide clear recommendations at the end
- Do not repeat previous content
[Web Search Results]
{search_section if search_section else "No search results"}

[User Requirements]
{user_input}

[Work Results from Each Agent]
"""
            for i, res in enumerate(valid_results):
                integration_context += f"\nAGENT {i+2} WORK:\n{res}\n"
            integration_context += f"""
[Your Task]
Based on all the above information, provide a **concise, complete, professional** report.

Requirements:
1. Clear structure, use headings for sections
2. Prioritize high-confidence facts
3. Provide clear recommendations at the end
4. If data comes from search results, label [Source: Search Result X]
5. If data is not in search results, label [Source: Agent Inference]

Please begin writing the final report:
"""
            general_agent_obj = Agent_table.get("agent_0")
            if not general_agent_obj:
                general_agent_obj = Agent_table.get("analyzer")
            if general_agent_obj:
                integration_node = Node(999, general_agent_obj)
                integration_node.description = "Final Integration"
                final_result = integration_node.send_msg(integration_context)
                final_result = self.safe_text(final_result)
                self.add_to_results(results, "final_integration", final_result)
                collaboration_chain.append("final_integration")
                print("Result integration complete")
            else:
                print("Error: Cannot find general agent for integration")
                final_result = "Unable to complete result integration"
        except Exception as e:
            print(f"Result integration exception: {e}")
            final_result = f"Result integration failed: {e}"
        try:
            self.final_result = self.generate_enhanced_report(results, collaboration_chain, user_input, final_result)
        except Exception as e:
            print(f"Error generating report: {e}")
            self.final_result = self.generate_basic_report(collaboration_chain, user_input, final_result)
        
        print("\n··················· Collaboration Complete ···················")
    def execute_parallel_task(self, task_info: Tuple) -> Tuple[str, str]:
        """Execute parallel task"""
        agent_name, node, index, root_analysis, user_input = task_info
        with self.print_lock:
            print(f">>>> {agent_name} starting execution")
        try:
            task_desc = node.description
            agent_context = self.build_tree_context(user_input, task_desc, root_analysis, agent_name, index)
            with self.print_lock:
                print(f">>>> {agent_name} sending request...")
            result = node.send_msg(agent_context)
            result = self.safe_text(result)
            with self.print_lock:
                print(f">>>> {agent_name} request complete")
            return (agent_name, result)
        except Exception as e:
            with self.print_lock:
                print(f">>>> {agent_name} execution exception: {e}")
            return (agent_name, f"{agent_name}: Execution exception - {str(e)}")
    def build_tree_context(self, user_input: str, task_desc: str, root_analysis: str, agent_name: str, agent_index: int) -> str:
        search_section = ""
        question_section = user_input
        # Extract [Web Search Results] section
        if "[Web Search Results]" in user_input and "[User Question]" in user_input:
            parts = user_input.split("[User Question]")
            search_section = parts[0]  # Section containing [Web Search Results]
            question_section = "[User Question]" + parts[1] if len(parts) > 1 else user_input
        guidance_map = {
            "analyzer": "As an analysis expert, please deeply analyze all aspects of the task and provide a detailed analysis report.",
            "planner": "As a planning expert, please develop a detailed execution plan, including timeline and resource allocation.",
            "executor": "As an execution expert, please provide specific implementation plans and operational steps.",
            "reviewer": "As a review expert, please evaluate quality and provide improvement suggestions.",
            "meta": "As a meta agent, please coordinate tasks and provide a guiding framework.",
            "agent_0": "As a general agent, please handle the assigned task and provide professional solutions.",
            "researcher": "As a researcher, please collect and organize accurate factual information, providing data support.",
            "financial": "As a financial analyst, please analyze financial data and provide professional financial analysis.",
            "risk": "As a risk assessor, please identify and evaluate various risks, providing risk analysis reports.",
            "technical": "As a technical expert, please analyze technical aspects and provide technical insights.",
            "creative": "As a creative expert, please provide innovative ideas and solutions."
        }
        guidance = guidance_map.get(agent_name, "Please complete the assigned task.")
        context = f"""[IMPORTANT INSTRUCTIONS - MUST FOLLOW]
1. You must **strictly base your answer on the following [Web Search Results]**
2. **All data, numbers, facts must come from search results**, do not fabricate
3. If the required information is not found in search results, explicitly state "Relevant information not found in search results"
4. Do not add data beyond search results

[Web Search Results]
{search_section if search_section else "No search results"}

[User Question]
{question_section}

[Root Node Analysis Reference]
{root_analysis if root_analysis else "None"}

[Your Role]
{guidance}

[Your Specific Task]
{task_desc}

[Output Requirements]
- Focus on your professional domain
- All data must come from search results
- Provide detailed, professional output
- Provide valuable input for final integration
- Use English for output
"""
        return context
    def add_to_results(self, results: Dict[str, List[str]], agent_name: str, result: str):
        if agent_name not in results:
            results[agent_name] = []
        results[agent_name].append(result)
    def generate_enhanced_report(self, results: Dict[str, List[str]], collaboration_chain: List[str], user_input: str, final_result: str) -> str:
        report = "·······················································\n"
        report += "         MULTI-AGENT COLLABORATION REPORT         \n"
        report += "·······················································\n\n"
        report += f"TASK: {user_input}\n\n"
        report += "COLLABORATION ARCHITECTURE:\n"
        report += "·······················\n"
        report += f"- Total Agents: {len(collaboration_chain)}\n"
        report += "- Architecture: Tree Structure\n"
        report += "- Coordination: Hierarchical with Parallel Execution\n\n"
        report += "AGENT CONTRIBUTIONS:\n"
        report += "···············\n"        
        for i, agent_name in enumerate(collaboration_chain):
            if agent_name == "final_integration":
                continue                
            if agent_name.startswith("verification") or "verification" in agent_name.lower():
                agent_role = "Verification Agent"
                display_name = agent_name
            else:
                agent_role = self.get_agent_role_description(agent_name)
                display_name = agent_name        
            report += f"\n{i+1}. {agent_role} ({display_name}):\n" 
            agent_results = results.get(agent_name, [])
            if agent_results:
                result_text = agent_results[-1]
                report += result_text + "\n"
            else:
                report += "No results available.\n"
        report += "              FINAL INTEGRATED RESULT              \n"
        report += final_result + "\n\n"
        report += "·······················································\n"
        report += "           COLLABORATION COMPLETE           \n"
        report += "·······················································\n"
        return report
    def get_agent_role_description(self, agent_name: str) -> str:
        role_map = {
            "meta": "Meta Agent - System Architect",
            "analyzer": "Analysis Expert",
            "planner": "Planning Expert",
            "executor": "Execution Expert",
            "reviewer": "Review Expert",
            "mindmap": "Mindmap Expert",
            "agent_0": "General Agent",
            "final_integration": "Final Integration",
            "researcher": "Research Expert",
            "financial": "Financial Analyst Expert",
            "risk": "Risk Assessment Expert",
            "technical": "Technical Expert",
            "creative": "Creative Expert",
            "verification": "Verification Agent"
        }
        return role_map.get(agent_name, agent_name)
    def get_agent_name(self, agent: Agent) -> str:
        for agent_name, table_agent in Agent_table.items():
            if table_agent.agent_description == agent.agent_description:
                return agent_name
        return "unknown"
    def ensure_agents_initialized(self):
        if not Agent_table:
            try:
                agent_init()
                print("Agents initialized successfully from agent_init.py")
            except Exception as e:
                print(f"Unable to initialize from agent_init.py: {e}")
                self.initialize_agents()
    def initialize_agents(self):
        llm_params = ["temperature", "0.7", "max_tokens", "2048", "stream", "false"]
        if "analyzer" not in Agent_table:
            default_analyzer = Agent(
                "You are an analysis expert, skilled in deeply analyzing user requirements and identifying key elements. Please respond in English.",
                LLM(
                    "http://localhost:11434/api/chat", 
                    "",
                    "qwen2.5:7b-instruct-q4_K_M",
                    llm_params
                ),
                [],
                "Analysis Expert"
            )
            Agent_table["analyzer"] = default_analyzer
        if "planner" not in Agent_table:
            default_planner = Agent(
                "You are a planning expert, skilled in creating detailed plans and reasonably allocating tasks. Please respond in English.",
                LLM(
                    "http://localhost:11434/api/chat", 
                    "",
                    "qwen2.5:7b-instruct-q4_K_M",
                    llm_params
                ),
                [],
                "Planning Expert"
            )
            Agent_table["planner"] = default_planner
        if "executor" not in Agent_table:
            default_executor = Agent(
                "You are an execution expert, skilled in specific implementation operations and generating high-quality results. Please respond in English.",
                LLM(
                    "http://localhost:11434/api/chat", 
                    "",
                    "qwen2.5:7b-instruct-q4_K_M",
                    llm_params
                ),
                [],
                "Execution Expert"
            )
            Agent_table["executor"] = default_executor
        if "reviewer" not in Agent_table:
            default_reviewer = Agent(
                "You are a review expert, skilled in examining work quality and proposing improvement suggestions. Please respond in English.",
                LLM(
                    "http://localhost:11434/api/chat", 
                    "",
                    "qwen2.5:7b-instruct-q4_K_M",
                    llm_params
                ),
                [],
                "Review Expert"
            )
            Agent_table["reviewer"] = default_reviewer
        if "agent_0" not in Agent_table:
            default_general = Agent(
                "You are a general agent capable of handling various tasks including analysis, planning, execution, etc. Please respond in English.",
                LLM(
                    "http://localhost:11434/api/chat", 
                    "",
                    "qwen2.5:7b-instruct-q4_K_M",
                    llm_params
                ),
                [],
                "General Agent"
            )
            Agent_table["agent_0"] = default_general
    def get_default_plan(self, user_input: str) -> str:
        return f'{{"task_list":[{{"task_id":"1","description":"Analyze user requirements: {user_input}","assigned_agent":"analyzer"}},{{"task_id":"2","description":"Create solution plan","assigned_agent":"planner"}},{{"task_id":"3","description":"Generate specific implementation plan","assigned_agent":"executor"}},{{"task_id":"4","description":"Review solution quality","assigned_agent":"reviewer"}}],"task_graph":{{"nodes":["1","2","3","4"],"edges":[{{"from":"1","to":"2"}},{{"from":"2","to":"3"}},{{"from":"3","to":"4"}}]}} }}'
    def safe_text(self, text: str) -> str:
        if not text:
            return ""
        return text.strip()
    def generate_basic_report(self, collaboration_chain: List[str], user_input: str, final_result: str) -> str:
        report = "······································································\n"
        report += "   Multi-Agent Collaboration Report   \n"
        report += "·································································\n\n"
        report += f"User Requirement: {user_input}\n\n"
        report += "Collaboration Process:\n"
        for i, agent in enumerate(collaboration_chain):
            report += f"{i+1}. {agent} Agent\n"
        report += "              FINAL RESULT              \n"
        report += final_result + "\n\n"
        report += "·························\n"
        report += "     Report Complete        \n"
        report += "·························\n"
        return report
    def result(self) -> str:
        return self.final_result