# multi_agent/AgentAPI.py
from graph import workflow
from models import LLM
import json
import requests
from typing import Optional, Dict, List
import time
import re
class AgentAPI:
    def __init__(self, enable_search: bool = True):
        self.is_initialized = False
        self.internet_available = True
        self.llm = None
        self.search_api_key = 'your-own-key'  # Replace with your actual API key
        self.search_url = "https://google.serper.dev/search"
        self.enable_search = enable_search 
    def ask(self, question: str) -> str:
        """Main Entry: Intelligent planning of multiple searches"""
        if not self.is_initialized:
            self.initialize()
        self.check_internet()
        print(f"[AgentAPI]Network status: {'Available' if self.internet_available else 'Check failed, continuing to try'}")
        if not self.enable_search:
            print("\n[AgentAPI]Web search is disabled, processing directly with multi-agent")
            return self.process_internally(question)
        search_queries = self.plan_search_queries(question)
        if search_queries is None:
            print("[AgentAPI]Unable to generate search strategy, using multi-agent directly for processing")
            return self.process_internally(question)
        if len(search_queries) == 0:
            print("[AgentAPI]No search query generated, using multi-agent directly for processing")
            return self.process_internally(question)
        print(f"[AgentAPI]Planning to execute {len(search_queries)} searches")
        for i, q in enumerate(search_queries, 1):
            print(f" Search {i}: {q}")
        all_results = []
        for i, query in enumerate(search_queries, 1):
            print(f"\n[AgentAPI]Search {i}: {query}")
            results = self.execute_search(query, num_results=5)
            if results:
                all_results.append({
                    'query': query,
                    'results': results,
                    'index': i
                })
                print(f"  Retrieved {len(results)} results")
            else:
                print(f"  Search {i} returned no results")
        if all_results:
            enhanced_question = self.build_enhanced_question(question, all_results)
            print(f"\n[AgentAPI]Completed {len(all_results)} successful searches, injecting search results into multi-agent system")
            return self.process_internally(enhanced_question)
        else:
            print("\n[AgentAPI]No search results")
            return self.process_internally(question)
    def initialize(self):
        self.is_initialized = True
        print("System initialization complete")
        if self.enable_search:
            print("[AgentAPI]Web search function is enabled")
        else:
            print("[AgentAPI]Web search function is disabled")
        try:
            params = ["temperature", "0.3", "max_tokens", "1024", "stream", "false"]
            self.llm = LLM(
                "http://localhost:11434/api/chat",
                "",
                "qwen2.5:7b-instruct-q4_K_M",
                params
            )
            print("AgentAPI local LLM initialized successfully")
        except Exception as e:
            print(f"AgentAPI local LLM initialization failed: {e}")
            self.llm = None
    def check_internet(self) -> bool:
        """Check network connection - using Google"""
        try:
            response = requests.get("https://www.google.com", timeout=3)
            self.internet_available = True
            print(f"[AgentAPI]Network connection successful (Google)")
            return True
        except Exception as e:
            print(f"[AgentAPI]Network check failed: {e}")
            self.internet_available = False
            return False
    def plan_search_queries(self, question: str) -> Optional[List[str]]:
        """
        Return list of search queries, return None on failure
        """
        if not self.llm:
            print("[AgentAPI]Local LLM not initialized, unable to generate search strategy")
            return None
        prompt = f"""You are a search strategy expert. Please analyze the user question below and decide how many searches are needed and what to search for each time.

User question: {question}

Requirements:
1. Analyze what information aspects are needed for the question (e.g., Company A's market value, Company B's revenue, industry trends, etc.)
2. Decide the number of searches (suggest 3-5 times)
3. Generate a specific search query for each search
4. Return format: Pure JSON array, e.g., ["query1", "query2", "query3", ...]

Important principles:
- Each search should target different aspects of the question
- Queries should be specific and precise to help search engines find high-quality information
- If the question involves multiple companies, search for each company separately
- If the question involves multiple dimensions (market value, revenue, risks, etc.), search for each dimension separately

Return only the JSON array, no other text."""
        try:
            response = self.call_llm(prompt)
            if not response:
                print("[AgentAPI]LLM call returned empty")
                return None
            # Extract JSON array
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                print(f"[AgentAPI]LLM returned format error: {response[:100]}...")
                return None
            queries = json.loads(json_match.group())
            if not isinstance(queries, list):
                print("[AgentAPI]LLM returned not an array")
                return None
            if len(queries) == 0:
                print("[AgentAPI]LLM returned empty array")
                return None
            return queries[:5]
        except json.JSONDecodeError as e:
            print(f"[AgentAPI]JSON parsing failed: {e}")
            return None
        except Exception as e:
            print(f"[AgentAPI]Search planning exception: {e}")
            return None
    def call_llm(self, prompt: str) -> Optional[str]:
        """Call local LLM (only for search planning)"""
        if not self.llm:
            return None
        try:
            payload = {
                "model": "qwen2.5:7b-instruct-q4_K_M",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": 0.3,
                "max_tokens": 512
            }
            response = requests.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "")
            else:
                print(f"[AgentAPI]LLM call failed, status code: {response.status_code}")
                return None
        except requests.Timeout:
            print("[AgentAPI]LLM call timeout")
            return None
        except Exception as e:
            print(f"[AgentAPI]Exception calling LLM: {e}")
            return None
    def execute_search(self, query: str, num_results: int = 5) -> List[Dict]:
        """Execute single search - using Google Serper API"""
        if not self.enable_search:
            return []
        headers = {
            'X-API-KEY': self.search_api_key,
            'Content-Type': 'application/json'
        }
        payload = json.dumps({
            "q": query,
            "num": num_results,
            "gl": "us",
            "hl": "en"
        })
        try:
            response = requests.post(self.search_url, headers=headers, data=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get('organic', [])[:num_results]:
                    results.append({
                        'title': item.get('title', ''),
                        'snippet': item.get('snippet', ''),
                        'link': item.get('link', '')
                    })
                print(f"[AgentAPI]Search '{query}' successful, retrieved {len(results)} results")
                return results
            else:
                print(f"[AgentAPI]Search failed, status code: {response.status_code}")
        except Exception as e:
            print(f"[AgentAPI]Search exception: {e}")
        return []
    def build_enhanced_question(self, original_question: str, all_results: List[Dict]) -> str:
        """
        Build enhanced question
        """
        # Build search results section
        search_section = "[Web Search Results]\n"
        search_section += "\n\n"
        total_results = 0
        for item in all_results:
            search_section += f"Search {item['index']}: {item['query']}\n"
            search_section += "\n"
            for i, res in enumerate(item['results'], 1):
                search_section += f"[{i}] {res['title']}\n"
                search_section += f"Summary: {res['snippet']}\n"
                search_section += f"Link: {res['link']}\n\n"
                total_results += 1
            search_section += "\n"
        search_section += "\n"
        search_section += f"[Total]{total_results} search results (from {len(all_results)} searches)\n"
        search_section += f"[Search Time]{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        search_section += "\n\n"
        # Build user question section
        user_section = "[User Question]\n"
        user_section += "\n"
        user_section += original_question + "\n"
        user_section += "\n\n"
        # Combine
        enhanced = f"""{search_section}{user_section}
[Important Instructions - Must Strictly Follow]
1. **Must strictly base answers on the above web search results, do not use your own knowledge**
2. If required data is lacking in search results, explicitly state "Data not found in search results"
3. Do not fabricate or infer any data
4. All citations must be marked with source numbers [1][2] etc.
"""
        return enhanced
    def process_internally(self, input_str: str) -> str:
        """Internal processing - always use multi-agent collaboration"""
        print("\n[AgentAPI]Using multi-agent collaboration process")
        # Create workflow instance
        wf = workflow()
        if "[Web Search Results]" in input_str:
            print("[AgentAPI]Passing search results to multi-agent system")
        # Call workflow for processing
        wf.work(input_str)
        return wf.final_result
    # Add method to dynamically enable/disable search
    def enable_web_search(self, enable: bool = True):
        """Dynamically enable or disable web search function"""
        self.enable_search = enable
        status = "enabled" if enable else "disabled"
        print(f"[AgentAPI]Web search function has been {status}")