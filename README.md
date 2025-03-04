# GenerativeAIApp

GenerativeAIApp is a feature-rich desktop application built with PyQt5 that integrates generative AI capabilities to assist developers in code generation, modification, and project scaffolding. This project provides a modern multi-tab interface featuring a chat window for AI interactions, a code editor with live preview, a project scaffolding wizard, and additional dockable widgets such as an activity log and file explorer.

---

## Table of Contents

- [Overview](#overview)
- [Project Report](#project-report)
- [Features](#features)

---

## Overview

GenerativeAIApp was developed as part of my internship to demonstrate the integration of modern user interface design with advanced generative AI functionalities. The application leverages PyQt5 for a responsive and interactive GUI while incorporating Google Generative AI for code generation and modification tasks. Its modular design and robust features make it a valuable tool for developers needing a smart assistant for coding, debugging, and project management.

---

## Project Report

### Background
During my internship, I was tasked with creating an application that could not only serve as a code editor but also integrate generative AI to enhance developer productivity. The goal was to build a system that combined advanced natural language processing with practical development tools.

### Design & Architecture
- **Modern UI/UX:**  
  The application features a multi-tabbed interface with a clean layout. Key components include a chat interface for AI interactions, a code editor with syntax highlighting (extendable), a live preview for web code, and a customizable toolbar. A sidebar offers quick access to additional functionalities such as project scaffolding and an activity log.
  
- **Generative AI Integration:**  
  Using the Google Generative AI API, the application generates code snippets, modifies existing code based on user instructions, and even simulates fallback behavior if a model fails. The design accommodates multiple models, making it extensible for future integration with GPT-4, Anthropic Claude, or Mistral APIs.

- **Robust Backend & Threading:**  
  To ensure a responsive UI, long-running tasks such as API calls and code execution are handled by a thread pool. Custom signals facilitate communication between worker threads and the main application, allowing for live updates and error handling.

- **Security & Validation:**  
  Input validation, safe command execution, and a configurable security level are implemented to protect the system from malicious inputs and potentially dangerous commands.

### Achievements & Challenges
- **Achievements:**  
  - Designed and implemented a modular, scalable application structure.
  - Successfully integrated generative AI into the code generation workflow.
  - Developed a modern, intuitive user interface using PyQt5 with multiple interactive components.
  
- **Challenges:**  
  - Ensuring responsiveness by managing multiple background threads without freezing the UI.
  - Integrating a fallback mechanism for API failures.
  - Maintaining code modularity and security throughout the project.

---

## Features

- **Modern User Interface:**  
  Multi-tabbed layout with a chat interface, live code preview, and an integrated code editor.

- **Generative AI Capabilities:**  
  Leverages Google Generative AI for code generation and modification. Supports multiple models with fallback options.

- **Project Scaffolding Wizard:**  
  Guides users through creating a new project with customizable templates and dependency management (stubbed for future extension).

- **Activity Logging:**  
  Maintains an activity log for auditing purposes with the ability to export logs.

- **Safe Execution & Auto-Save:**  
  Implements safe command execution for terminal tasks and an auto-save feature for the code editor.

- **Customizable Themes:**  
  Supports light, dark, and high contrast modes to suit user preferences.

---


