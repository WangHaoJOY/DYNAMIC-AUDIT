# multi_agent/hierarchical.py
from typing import List, Dict, Tuple
import time
import json
import threading
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from agent_init import Agent_table
from AgentAPI import AgentAPI
from models import Agent, LLM
# Utility Functions
import requests
def call_ollama(payload: dict, timeout: int = 300) -> dict | None:
    """Call Ollama API"""
    try:
        response = requests.post("http://localhost:11434/api/chat", json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f" Ollama call failed: {e}")
        return None
def search_web(query: str, num_results: int = 3) -> list[dict]:
    """Execute web search (using Serper API)"""
    api_key = 'your-own-key'  # Replace with your Serper API key
    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    payload = json.dumps({
        "q": query,
        "num": num_results,
        "gl": "us",
        "hl": "en"
    })
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get('organic', [])[:num_results]:
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'link': item.get('link', '')
                })
            return results
    except Exception as e:
        print(f" Search failed: {e}")
    return []
# Data Class Definitions
@dataclass
class AuditItem:
    """Item to be audited"""
    part: str
    reason: str
    verification_task: str
    original_text: str
    is_suspicious: bool = True  # Mark if it's a suspicious point
@dataclass
class VerificationResult:
    """Verification result"""
    part: str
    corrected: str
    confidence: str  # "High", "Medium", "Low"
    sources: str
    agent_name: str = ""  # Agent name
    agent_type: str = "verification"  # Agent type, default is verification
    verifier_id: int = 0  # Verifier ID
    is_correct: bool = True  # mark if original content is correct
# Optimized Audit Class
class HierarchicalMAS:
    """Two-layer recursive multi-agent system (Audit Version - Optimized)"""
    def __init__(self, 
                 use_sequential: bool = True,
                 enable_search: bool = True,
                 model_name: str = "qwen2.5:7b-instruct-q4_K_M"):
        self.use_sequential = use_sequential
        self.enable_search = enable_search
        self.model_name = model_name
        self.print_lock = threading.Lock()
        from agent_init import agent_init
        if not Agent_table:
            print("Initializing agent table...")
            agent_init()
            print(f"Agent table initialization complete, contains {len(Agent_table)} agents")
        self._ensure_meta_agent()
    def _ensure_meta_agent(self):
        if "meta" not in Agent_table:
            print("Upper-level meta agent does not exist")
    def _estimate_complexity(self, task: str, report: str) -> str:
        total_len = len(task) + len(report)
        if total_len < 2000:
            return "low"
        elif total_len < 5000:
            return "medium"
        else:
            return "high"
    def run_main_system(self, task: str) -> str:
        """Run main system once, generate complete report"""
        print("\n[Phase 1]Running main system to generate initial report")
        api = AgentAPI(enable_search=self.enable_search)
        report = api.ask(task)
        print("Main system execution complete")
        return report
    def _audit_with_llm(self, full_report: str, max_items: int, reason: str = "") -> Tuple[List[AuditItem], str]:
        """Directly audit with LLM (fallback solution)"""
        fallback_marker = "[Fallback]Using direct LLM audit"
        if reason:
            fallback_marker += f" - Reason: {reason}"
        print(f" {fallback_marker}")
        params = ["temperature", "0.2", "max_tokens", "1024", "stream", "false"]
        llm = LLM(
            url="http://localhost:11434/api/chat",
            api_key="",
            model_name=self.model_name,
            params=params
        )
        temp_agent = Agent(
            sys_prompt="You are an audit expert specializing in identifying claims that need verification.",
            base_LLM=llm,
            tools=[],
            agent_description="Audit Agent (Fallback)"
        )
        prompt = f"""You are an Audit Agent. Your task is to analyze the following report and identify up to {max_items} specific parts that need verification.
Report:
{full_report}

Identify parts that:
1. Contain numerical data without clear sources (e.g., revenue figures, market share percentages)
2. Use uncertain language (e.g., "approximately", "about", "maybe", "estimated")
3. Seem logically inconsistent or contradict other parts
4. Would significantly impact the conclusion if wrong

For each identified part, output a JSON array with exactly this structure:
[
  {{
    "part": "The exact sentence or phrase to verify",
    "reason": "Why this needs verification (e.g., 'No source cited for revenue figure')",
    "verification_task": "A specific question for a verification agent to answer (e.g., 'What was Tesla's actual Q4 2024 revenue according to official reports?')"
  }}
]

Requirements:
- Output EXACTLY 1-{max_items} items
- Be specific about what to verify
- The verification_task should be self-contained and answerable

Return ONLY the JSON array, no other text."""
        try:
            response = temp_agent.send_msg2agent(prompt)
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                import json
                items = json.loads(json_match.group())
                audit_items = []
                for item in items:
                    audit_items.append(AuditItem(
                        part=item.get("part", ""),
                        reason=item.get("reason", ""),
                        verification_task=item.get("verification_task", ""),
                        original_text=item.get("part", "")
                    ))
                return audit_items, fallback_marker
        except Exception as e:
            print(f"Fallback audit failed: {e}")
        return [], fallback_marker + " (Audit execution failed)"
    def _should_audit_task(self, task: str) -> Tuple[bool, str]:
        """
        Let LLM determine if the current task needs audit
        Returns (needs_audit, reason)
        """
        print("\n[Task Type Assessment]Analyzing whether task needs audit...")
        prompt = f"""You are a task classifier. Analyze the following user task and determine whether it needs factual verification (audit).

User task: {task}

A task NEEDS audit if it:
1. Asks for financial data (revenue, profit, cash flow, etc.)
2. Asks for numerical data or statistics
3. Asks for factual information with specific numbers
4. Involves analysis of companies, markets, or policies
5. Requires verification of claims or data

A task does NOT need audit if it:
1. Asks for explanations of concepts or theories
2. Asks for creative content (travel plans, stories, ideas)
3. Asks for opinions or predictions without factual basis
4. Asks for general knowledge without specific data points

Return ONLY a JSON object with this structure:
{{
  "needs_audit": true or false,
  "reason": "Brief explanation of your decision",
  "task_type": "financial/data/knowledge/creative/other"
}}
"""
        try:
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 200,
                "stream": False
            }
            response = call_ollama(payload)
            if response and "message" in response:
                content = response["message"]["content"].strip()
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    needs_audit = result.get("needs_audit", False)
                    reason = result.get("reason", "")
                    task_type = result.get("task_type", "unknown")
                    print(f"  Assessment result: {'Needs audit' if needs_audit else 'Skip audit'}")
                    print(f"  Task type: {task_type}")
                    print(f"  Reason: {reason}")
                    return needs_audit, reason
        except Exception as e:
            print(f"{e}")
        return True, "Default to needing audit (assessment failed)"
    # Let LLM identify suspicious points
    def _identify_suspicious_statements_llm(self, report: str, max_items: int = 5) -> List[Dict]:
        """
        Let LLM identify suspicious points in the report that need verification
        No hardcoding, fully determined by LLM
        """
        print(f"\n[Phase 2-Optimized]LLM identifying suspicious points (max {max_items})")
        report_preview = report[:5000] + "..." if len(report) > 5000 else report
        prompt = f"""You are an audit expert. Analyze the following report and identify up to {max_items} statements that need verification.

Report:
{report_preview}

Identify statements that:
1. Contain numerical data (prices, revenues, percentages) without clear sources
2. Use uncertain language (maybe, perhaps, approximately, estimated)
3. Make factual claims that could be wrong
4. Would significantly impact the conclusion if incorrect

For each identified statement, output a JSON array with this structure:
[
  {{
    "part": "The exact sentence to verify",
    "reason": "Why this needs verification",
    "verification_task": "A specific question to verify this claim"
  }}
]

Return ONLY the JSON array, no other text.
"""
        try:
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1000,
                "stream": False
            }
            response = call_ollama(payload)
            if response and "message" in response:
                content = response["message"]["content"].strip()
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    items = json.loads(json_match.group())
                    print(f"  Identified {len(items)} suspicious points")
                    for i, item in enumerate(items):
                        print(f"    {i+1}. {item.get('reason', '')[:80]}...")
                    return items
        except Exception as e:
            print(f"Suspicious point identification failed: {e}")
        return []
    def _verify_sentence_with_search(self, sentence: str, verification_task: str, search_results: list) -> Dict:
        """
        Sentence verification with search results - force use of search results
        """
        # Build search results context
        search_context = ""
        if search_results:
            search_context = "[Real-time Search Results - MUST use first]\n" + "\n".join(
                f"[{i+1}] {r['title']}\nSummary: {r['snippet']}\nLink: {r['link']}\n"
                for i, r in enumerate(search_results)
            ) + "\n\n"
        else:
            search_context = "[Warning]No search results, use your knowledge but mark 'No search results'\n"
        prompt = f"""{search_context}
    [Verification Task]
    Please verify the accuracy of the following statement:

    Statement: "{sentence}"

    Verification task: {verification_task}

    [Mandatory Instructions - Must Follow]
    1. **Must prioritize using data from [Real-time Search Results]**
    2. If search results contain clear data, use search results as the standard
    3. Only use your own knowledge if search results have absolutely no relevant information, but must mark "Based on knowledge inference"
    4. Do not fabricate data

    [Return Format]
    Return a strict JSON object with the following structure:
    {{
  "is_correct": true or false,
  "corrected": "Confirmed correct" or corrected version,
  "confidence": "High" or "Medium" or "Low",
  "evidence": "Explanation of basis, cite search result numbers or explain knowledge source"
    }}
    """
        try:
            payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 500,
            "stream": False
            }
            response = call_ollama(payload)
            if response and "message" in response:
                content = response["message"]["content"].strip()
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            print(f"Sentence verification failed: {e}")
        return {
        "is_correct": True, 
        "corrected": sentence, 
        "confidence": "Low",
        "evidence": "Verification failed, using original sentence"
        }
    # Optimized Audit Main Function
    def audit_report_optimized(self, full_report: str, task: str = "") -> Tuple[List[AuditItem], str]:
        """
        Optimized audit: First determine task type, then identify suspicious points
        """
        print("\n[Phase 2-Optimized Version]Audit agent analyzing report")
        # 1. Determine if task needs audit
        needs_audit, audit_reason = self._should_audit_task(task if task else full_report[:500])
        if not needs_audit:
            print(f"Task type does not need audit, skipping")
            return [], f"[Skip]{audit_reason}"
        # 2. Identify suspicious points
        suspicious_items = self._identify_suspicious_statements_llm(full_report, max_items=5)
        if not suspicious_items:
            print("No suspicious points found, skipping audit")
            return [], "[Skip]No suspicious content"
        # 3. Convert to AuditItem
        audit_items = []
        for item in suspicious_items:
            audit_items.append(AuditItem(
                part=item.get("part", ""),
                reason=item.get("reason", ""),
                verification_task=item.get("verification_task", ""),
                original_text=item.get("part", ""),
                is_suspicious=True
            ))
        return audit_items, f"[Optimized Audit]Found {len(audit_items)} suspicious points"
    def verify_item(self, item: AuditItem, verifier_id: int) -> VerificationResult:
        agent_name = f"Verification Agent {verifier_id}"
        print(f"    {agent_name} starting verification: {item.part[:50]}...")
        try:
            # First call search separately (search only this audit item's verification_task)
            search_results = search_web(item.verification_task, num_results=3)
            # Use verification with search
            result = self._verify_sentence_with_search(item.part, item.verification_task, search_results)
            is_correct = result.get("is_correct", True)
            corrected = result.get("corrected", item.part)
            confidence = result.get("confidence", "Medium")
            evidence = result.get("evidence", "No source explanation")
            # If there are search results, automatically boost confidence
            if search_results and confidence != "Low" and is_correct:
                confidence = "High"
            sources = evidence
            if search_results:
                sources += f" (Based on {len(search_results)} search results)"
            return VerificationResult(
                part=item.part,
                corrected=corrected,
                confidence=confidence,
                sources=sources,
                agent_name=agent_name,
                agent_type="verification_with_search",
                verifier_id=verifier_id,
                is_correct=is_correct
            )
        except Exception as e:
            print(f"Verification failed: {e}")
        # Fallback return
        return VerificationResult(
            part=item.part,
            corrected=item.part,
            confidence="Low",
            sources="Verification failed",
            agent_name=agent_name,
            agent_type="verification",
            verifier_id=verifier_id,
            is_correct=True
        )
    def verify_items(self, audit_items: List[AuditItem]) -> List[VerificationResult]:
        """
        For each audit item, verify with 2 verification agents in parallel
        """
        print(f"\n[Phase 3]Parallel verification of {len(audit_items)} audit items")
        all_results = []        
        for item_idx, item in enumerate(audit_items):
            print(f"\nVerifying audit item {item_idx+1}: {item.part[:100]}...")
            # Launch 2 verification agents in parallel for each audit item
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for i in range(2):
                    future = executor.submit(self.verify_item, item, i+1)
                    futures.append(future)
                # Collect results
                results = []
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        print(f"Verification thread exception: {e}")
                # Take majority decision
                if results:
                    # Filter verification results where original content is correct
                    correct_results = [r for r in results if r.is_correct]
                    if correct_results:
                        # If majority thinks correct, take the one with highest confidence
                        best_result = max(correct_results, key=lambda x: 
                                         0 if x.confidence == "High" else 
                                         1 if x.confidence == "Medium" else 2)
                        all_results.append(best_result)
                        print(f"Verification complete, content correct")
                    else:
                        # If all think incorrect, take the corrected version
                        best_result = max(results, key=lambda x: 
                                         0 if x.confidence == "High" else 
                                         1 if x.confidence == "Medium" else 2)
                        all_results.append(best_result)
                        print(f"Verification complete, needs correction")
        return all_results
    def apply_corrections(self, full_report: str, verifications: List[VerificationResult]) -> str:
        """Apply verification results to original report (only correct errors, skip correct ones)"""
        print("\n[Phase 4]Applying corrections")
        corrected_report = full_report
        for ver in verifications:
            if not ver.is_correct and ver.corrected != ver.part and ver.confidence != "Low":
                # Only correct wrong sentences
                pattern = re.escape(ver.part)
                corrected_report = re.sub(pattern, ver.corrected, corrected_report, count=1)
                print(f"Corrected: {ver.part[:50]}... → {ver.corrected[:50]}...")
            else:
                print(f"No correction needed: {ver.part[:50]}...")
        return corrected_report
    def _insert_verification_section(self, final_report: str, verifications: List[VerificationResult]) -> str:
        """Insert verification trace at the end of final report"""
        corrections = [v for v in verifications if not v.is_correct]
        if not corrections:
            return final_report
        
        verification_section = "\n\n[Audit Verification Trace]\n"
        verification_section += "·"*60 + "\n"
        for i, ver in enumerate(corrections):
            verification_section += f"Verification {i+1} by {ver.agent_name}:\n"
            verification_section += f"  Original: {ver.part}\n"
            verification_section += f"  Corrected: {ver.corrected}\n"
            verification_section += f"  Confidence: {ver.confidence}\n"
            verification_section += f"  Source: {ver.sources}\n\n"
        return final_report + verification_section
    def solve(self, task: str) -> Dict:
        """
        Main entry: Audit version two-layer system (optimized version)
        """
        print("\n" + "·"*60)
        print("Two-layer multi-agent system starting (Audit Version - Optimized)")
        print("·"*60)
        overall_start = time.time()
        # 1. Run main system once
        main_start = time.time()
        full_report = self.run_main_system(task)
        main_time = time.time() - main_start
        print(f"Main system time: {main_time:.2f}s")
        # 2. Optimized audit
        audit_items, audit_marker = self.audit_report_optimized(full_report, task)
        # 3. If no audit points, return directly
        if not audit_items:
            print("\nAudit found no issues, returning main system report directly")
            return {
                "final_result": full_report,
                "execution_time": time.time() - overall_start,
                "main_time": main_time,
                "audit_time": 0,
                "verification_time": 0,
                "audit_items": [],
                "verifications": [],
                "audit_marker": audit_marker
            }
        verify_start = time.time()
        verifications = self.verify_items(audit_items)
        verify_time = time.time() - verify_start
        # 5. Apply corrections
        final_report = self.apply_corrections(full_report, verifications)
        # 6. Insert audit verification trace (only corrected errors)
        final_report = self._insert_verification_section(final_report, verifications)
        overall_end = time.time()
        print(f"\n" + "·"*60)
        print(f"Execution complete")
        print(f"Audit source: {audit_marker}")
        print(f"Total time: {overall_end - overall_start:.2f}s")
        print(f"Main system: {main_time:.2f}s")
        print(f"Audit: {verify_time:.2f}s ({len(audit_items)} audit items × {len(verifications)} verification agents)")
        print(f"Total time/Main system time: {(overall_end - overall_start)/main_time:.1f}x")
        print("·"*60)
        return {
            "final_result": final_report,
            "original_report": full_report,
            "execution_time": overall_end - overall_start,
            "main_time": main_time,
            "audit_time": verify_time,
            "audit_items": [a.__dict__ for a in audit_items],
            "verifications": [v.__dict__ for v in verifications],
            "audit_marker": audit_marker
        }
def create_hierarchical_mas(use_sequential: bool = True,
                           enable_search: bool = True) -> HierarchicalMAS:
    """Create audit version two-layer system"""
    return HierarchicalMAS(
        use_sequential=use_sequential,
        enable_search=enable_search
    )