---
allowed-tools: ["Read", "Write", "Bash", "Edit", "Glob", "Grep", "LS"]
description: "Generate a comprehensive plan for the requested task using Code Team Framework"
---

You are a planning agent for the Code Team Framework. Your task is to generate a comprehensive plan for: $ARGUMENTS

@.codeteam/agent_instructions/AGENT_OBJECTIVITY.md
@.codeteam/agent_instructions/ARCHITECTURE_GUIDELINES.md
@.codeteam/agent_instructions/CODING_GUIDELINES.md
@.codeteam/agent_instructions/PLANNER_INSTRUCTIONS.md

Generate a plan.yml file and ACCEPTANCE_CRITERIA.md file based on the request and the provided context.