# Architecture

## Purpose

AI Legal and Compliance Auditor is an evidence-first audit system for policy, legal, and compact financial disclosure documents.

It combines:

- Document parsing
- Local retrieval
- Tool-driven evidence collection
- Structured LLM audit generation
- Self-consistency consensus
- Independent LLM-as-Judge evaluation
- Cloud deployment on AWS ECS Fargate

## Core Workflow

```text
Document Upload
      |
      v
Document Parser
      |
      v
Chunking
      |
      v
BM25 Evidence Index
      |
      v
Deterministic Rule Retrieval
      |
      v
Evidence Agent
      |
      v
Evidence Bundle
      |
      v
Structured Audit Candidates
      |
      v
Self-Consistency Consensus
      |
      v
Independent LLM Judge
      |
      v
Audit Envelope
      |
      v
Storage