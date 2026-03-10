# DYNAMIC-AUDIT: Self-Organizing Multi-Agent Framework with Explicit Auditing

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**DYNAMIC-AUDIT** is a novel multi-agent framework powered by local LLMs (Qwen2.5-7B) that features:

- **Runtime dynamic agent composition** via a meta-agent (2–6 agents, linear/parallel/tree structures)
- **Explicit post-hoc auditing layer** with dual independent verifiers, consensus adjudication, tri-level confidence (High/Medium/Low), and traceable audit trails
- Grounded generation using Serper Google Search API
- Designed for factual reliability and hallucination mitigation

This repository contains the **core framework implementation** as described in the paper:

> DYNAMIC-AUDIT: A Self-Organizing Multi-Agent Framework with an Explicit Auditing Mechanism  
> Hao Wang, Li Zhu, Lihua Tian, Tao Xie  
> Expert Systems with Applications (ESWA), 2026 (submitted/under review)

## Features

- Meta-agent dynamically decides agent count (2–6), roles (12 specializations), and topology
- Supports linear, parallel, and tree-structured collaboration
- Explicit auditing with parallel verification + mandatory consensus
- Full audit trails with claim-level corrections and confidence scoring
- Local LLM inference via Ollama (no cloud dependency for core logic)

## Requirements

### Hardware
- GPU with ≥8GB VRAM recommended (RTX 4060 8GB or better)
- 16GB+ RAM

### Software
- Python 3.10 or 3.11
- Ollama running locally with Qwen2.5:7b-instruct-q4_K_M model pulled

**API Key Configuration**
- Serper API key is intentionally set to 'your-own-key' as a placeholder.
- Replace it with your own key (get free from https://serper.dev).
- Recommended: use environment variable instead:
  export SERPER_API_KEY='your-real-key'
- Never commit your real key to Git!
