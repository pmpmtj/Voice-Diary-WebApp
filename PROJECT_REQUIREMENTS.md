# Project Requirements Document (PRD)
## Audio Diary Transcription System

### 1. Project Overview
The Audio Diary Transcription System is a comprehensive solution that combines audio processing, transcription, and web-based control. The system consists of two main components:
1. Core Transcription Pipeline (Python-based)
2. Web Interface (Django-based)

### 2. System Architecture

#### 2.1 Core Components
- **Audio Processing Pipeline**
  - Google Drive Integration
  - Local Whisper Transcription
  - OpenAI Processing
  - Scheduler System
  - File Management System

- **Web Interface**
  - Django-based Dashboard
  - Scheduler Control
  - User Management
  - Activity Monitoring

#### 2.2 Key Technologies
- Python 3.7+
- Django 5.1.7
- OpenAI API
- Local Whisper Model
- SQLite Database
- Bootstrap 5 (Frontend)

### 3. Development Guidelines

#### 3.1 Python Script Development
When creating new Python scripts, follow these guidelines:

1. **File Structure**
   - Place new scripts in the root directory
   - Follow the existing naming convention (lowercase with underscores)
   - Include a docstring with module description

2. **Code Standards**
   ```python
   """
   Module: [Module Name]
   Description: [Brief description of functionality]
   Author: [Your Name]
   Date: [Creation Date]
   """
   
   import logging
   from typing import Dict, List, Optional
   
   # Configure logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   logger = logging.getLogger(__name__)
   
   class NewComponent:
       def __init__(self, config: Dict):
           self.config = config
           self.logger = logging.getLogger(__name__)
   ```

3. **Configuration Management**
   - Use `config.json` for general settings
   - Create separate config files for specific components
   - Follow the existing pattern in `openai_config.py`

4. **Error Handling**
   - Implement proper exception handling
   - Log all errors with appropriate severity levels
   - Include user-friendly error messages

#### 3.2 Web Interface Development
When creating new web components:

1. **Django App Structure**
   ```
   new_component/
   ├── __init__.py
   ├── models.py
   ├── views.py
   ├── urls.py
   ├── forms.py
   └── templates/
       └── new_component/
           ├── base.html
           └── [component_name].html
   ```

2. **Template Guidelines**
   ```html
   {% extends "base.html" %}
   {% load crispy_forms_tags %}
   
   {% block content %}
   <div class="container">
       <h2>Component Title</h2>
       <form method="post">
           {% csrf_token %}
           {{ form|crispy }}
           <button type="submit" class="btn btn-primary">Submit</button>
       </form>
   </div>
   {% endblock %}
   ```

3. **View Development**
   ```python
   from django.views.generic import TemplateView
   from django.contrib.auth.mixins import LoginRequiredMixin
   
   class NewComponentView(LoginRequiredMixin, TemplateView):
       template_name = 'new_component/component.html'
       
       def get_context_data(self, **kwargs):
           context = super().get_context_data(**kwargs)
           # Add your context data here
           return context
   ```

### 4. Testing Requirements

1. **Python Scripts**
   - Include unit tests for new functionality
   - Test error handling and edge cases
   - Mock external API calls

2. **Web Components**
   - Write tests for views and models
   - Test user authentication
   - Include integration tests for API endpoints

### 5. Documentation Requirements

1. **Code Documentation**
   - Document all new functions and classes
   - Include type hints
   - Add usage examples in docstrings

2. **User Documentation**
   - Update relevant README files
   - Document new features in the web interface manual
   - Include setup instructions for new components

### 6. Security Guidelines

1. **Authentication**
   - Always use Django's authentication system
   - Implement proper permission checks
   - Follow the principle of least privilege

2. **Data Protection**
   - Never store sensitive data in plain text
   - Use environment variables for secrets
   - Implement proper input validation

### 7. Deployment Considerations

1. **Configuration**
   - Use environment-specific settings
   - Follow the existing configuration patterns
   - Document all configuration options

2. **Dependencies**
   - Update `requirements.txt` with new packages
   - Specify version numbers
   - Document any system-level requirements

### 8. Maintenance Guidelines

1. **Logging**
   - Use the existing logging system
   - Create appropriate log files
   - Implement log rotation

2. **Error Monitoring**
   - Implement proper error tracking
   - Set up alerts for critical errors
   - Maintain error logs

### 9. Version Control

1. **Git Workflow**
   - Create feature branches
   - Write descriptive commit messages
   - Follow the existing branching strategy

2. **Code Review**
   - Review all new code
   - Check for security vulnerabilities
   - Ensure documentation is complete

### 10. Project-Specific Guidelines

#### 10.1 Audio Processing
- Follow the existing patterns in `local_whisper.py` and `openai_whisper.py`
- Implement proper audio format validation
- Handle large files efficiently
- Include progress tracking for long-running operations

#### 10.2 Web Interface
- Maintain consistency with existing dashboard design
- Follow the patterns in `scheduler_control` app
- Implement real-time updates where appropriate
- Use Bootstrap 5 components for UI elements

#### 10.3 Configuration Files
- Follow the structure in `config.json`
- Document all configuration options
- Include default values
- Validate configuration on startup

#### 10.4 Logging Standards
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Include timestamps and context in log messages
- Implement log rotation for large files
- Follow the pattern in existing log files

This PRD provides a comprehensive guide for new team members to understand the project structure and requirements when creating new components. It maintains consistency with the existing codebase while ensuring best practices are followed. 