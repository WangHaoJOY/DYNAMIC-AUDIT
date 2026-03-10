# multi_agent/models.py
import json
import requests
from requests.models import Response
from typing import List
from dataclasses import dataclass

class LLM:
    def __init__(self, url: str = 'http://localhost:11434/api/chat',
                 api_key: str = '',
                 model_name: str = 'qwen2.5:7b-instruct-q4_K_M',
                 params: List[str] = None):
        self.url = url
        self.api_key = api_key
        self.model_name = model_name
        self.params = params or ["temperature", "0.7", "max_tokens", "512", "stream", "false"]
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
        return '{"type": "function","function":{"name": "' + self.name + '","description": "' + self.description + '","parameters":' + str_params + ',"strict":' + str(self.is_strict).lower() + '}},'
@dataclass
class Agent:
    sys_prompt: str
    base_LLM: LLM
    tools: List[tool]
    agent_description: str
    def send_load(self, load: str) -> Response:
        print(f"Preparing to send request to: {self.base_LLM.url}")
        print(f"Request body length: {len(load)}")        
        headers = {
            "Authorization": f"Bearer {self.base_LLM.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }        
        try:
            response = requests.post(
                self.base_LLM.url,
                headers=headers,
                data=load,
                timeout=None
            )
            print(f"Request completed, status code: {response.status_code}")
            return response
        except Exception as e:
            print(f"HTTP request exception: {e}")
            mock_resp = requests.Response()
            mock_resp.status_code = 503
            mock_resp._content = b'{"error": "network request failed"}'
            mock_resp.headers = {"Content-Type": "application/json"}
            return mock_resp
    def send_msg2agent(self, content_request: str) -> str:
        print(f"{self.agent_description} executing task...")    
        try:
            safe_content = content_request        
            clean_prompt = self.sys_prompt        
            request_body = {
                "model": self.base_LLM.model_name,
                "messages": [
                    {"role": "system", "content": clean_prompt},
                    {"role": "user", "content": safe_content}
                ],
                "temperature": 0.05, 
                "max_tokens": 1024, 
                "stream": False
            }
            # Add LLM params
            if self.base_LLM.params:
                for i in range(0, len(self.base_LLM.params), 2):
                    key = self.base_LLM.params[i]
                    value = self.base_LLM.params[i+1]
                    request_body[key] = value        
            content = json.dumps(request_body, ensure_ascii=False)        
            response = self.send_load(content)
            response_str = response.text        
            if response.status_code == 200:
                result = self.extract_content_simple(response_str)
                return result if result.strip() else f"{self.agent_description}: Request processed"
            else:
                return f"{self.agent_description}: API call failed (HTTP {response.status_code})"        
        except Exception as e:
            print(f"Message sending exception: {e}")
            return f"{self.agent_description}: Execution exception"   
    def extract_content_simple(self, response_str: str) -> str:
        try:
            if "}\n{" in response_str or '"done":false' in response_str:
                print("Detected streaming response, merging...")
                return self.extract_streaming_response(response_str)
            try:
                response_json = json.loads(response_str)
                if "message" in response_json and "content" in response_json["message"]:
                    content = response_json["message"]["content"]
                elif "choices" in response_json and len(response_json["choices"]) > 0:
                    content = response_json["choices"][0].get("message", {}).get("content", "")
                elif "content" in response_json:
                    content = response_json["content"]
                else:
                    content = self.extract_content_by_search(response_str)                
                return content                    
            except json.JSONDecodeError as e:
                print(f"JSON parsing failed, trying search extraction: {e}")
                return self.extract_content_by_search(response_str)                
        except Exception as e:
            print(f"Content extraction failed: {e}")
            return response_str    
    def extract_streaming_response(self, response_str: str) -> str:
        """Process streaming response, merge all chunks"""
        try:
            lines = response_str.strip().split('\n')
            full_content = ""            
            for line in lines:
                line = line.strip()
                if not line:
                    continue                    
                try:
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        chunk_content = data["message"]["content"]
                        chunk_content = chunk_content.replace('\\n', '\n').replace('\\"', '"')
                        full_content += chunk_content                        
                except json.JSONDecodeError:
                    continue
            if full_content:
                print(f"Merged {len(lines)} chunks from streaming response, content length: {len(full_content)}")
                try:
                    json.loads(full_content)
                    print("Merged content is valid JSON")
                except:
                    print("Merged content is not in JSON format")
                return full_content
            else:
                print("Could not extract any content from streaming response")
                return response_str       
        except Exception as e:
            print(f"Streaming response extraction failed: {e}")
            return response_str
    def extract_content_by_search(self, response_str: str) -> str:
        """Extract content by searching"""
        start_idx = response_str.find('"content":"') + 11
        if start_idx < 11:
            return response_str
        end_idx = start_idx
        in_escape = False
        while end_idx < len(response_str):
            c = response_str[end_idx]
            if not in_escape and c == '"':
                break
            if c == '\\':
                in_escape = not in_escape
            else:
                in_escape = False
            end_idx += 1
        if end_idx > start_idx:
            content = response_str[start_idx:end_idx]
            content = content.replace("\\n", "\n").replace("\\\"", "\"").replace("\\\\", "\\")
            return content
        return response_str
class Node:
    def __init__(self, ID: int, g_agent: Agent):
        self.UID = ID
        self.goal_agent = g_agent
        self.message = ""
        self.description = ""
    def setDescription(self, text: str):
        self.description = text
    def send_msg(self, msg: str) -> str:
        self.message = msg
        return self.goal_agent.send_msg2agent(self.message)
class Graph:
    def __init__(self):
        self.nodes: List[Node] = []
        self.adjacency_matrix: List[List[int]] = [[0]]
        self.node_count: int = 0
        self.topological_order: List[int] = []
    def setNumber(self, num: int):
        self.node_count = num
        self.adjacency_matrix = [[0 for _ in range(num)] for _ in range(num)]
    def add_node(self, node: Node):
        self.nodes.append(node)
        self.node_count += 1
        self.expand_matrix()
    def show_matrix(self):
        print("{")
        for row in self.adjacency_matrix:
            print("[", end="")
            for val in row:
                print(f"{val},", end="")
            print("]")
        print("}")
    def add_edge(self, from_uid: int, to_uid: int):
        from_idx = self.find_node_index(from_uid)
        to_idx = self.find_node_index(to_uid)
        if from_idx >= 0 and to_idx >= 0:
            self.adjacency_matrix[from_idx][to_idx] = 1
    def get_incoming_nodes(self, node_uid: int) -> List[int]:
        node_idx = self.find_node_index(node_uid)
        incoming = []
        if node_idx >= 0:
            for i in range(self.node_count):
                if self.adjacency_matrix[i][node_idx] == 1:
                    incoming.append(self.nodes[i].UID)
        return incoming
    def get_outgoing_nodes(self, node_uid: int) -> List[int]:
        node_idx = self.find_node_index(node_uid)
        outgoing = []
        if node_idx >= 0:
            for i in range(self.node_count):
                if self.adjacency_matrix[node_idx][i] == 1:
                    outgoing.append(self.nodes[i].UID)
        return outgoing
    def topological_sort(self):
        in_degree = [0] * self.node_count
        queue = []
        result = []
        for i in range(self.node_count):
            for j in range(self.node_count):
                if self.adjacency_matrix[i][j] == 1:
                    in_degree[j] += 1
        for i in range(self.node_count):
            if in_degree[i] == 0:
                queue.append(i)
        while queue:
            current = queue.pop(0)
            result.append(self.nodes[current].UID)
            for j in range(self.node_count):
                if self.adjacency_matrix[current][j] == 1:
                    in_degree[j] -= 1
                    if in_degree[j] == 0:
                        queue.append(j)

        self.topological_order = result
    def find_node_index(self, uid: int) -> int:
        for i in range(len(self.nodes)):
            if self.nodes[i].UID == uid:
                return i
        return -1
    def expand_matrix(self):
        new_matrix = [[0 for _ in range(self.node_count)] for _ in range(self.node_count)]
        for i in range(len(self.adjacency_matrix)):
            for j in range(len(self.adjacency_matrix[0])):
                new_matrix[i][j] = self.adjacency_matrix[i][j]
        self.adjacency_matrix = new_matrix