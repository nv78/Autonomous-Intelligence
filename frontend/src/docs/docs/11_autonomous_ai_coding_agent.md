# Autonomous AI Coding Agent

The **Autonomous AI Coding Agent**  is designed to streamline the software development process by autonmously analyzing an exisiting local codebase, generating and implementing a feature into the codebase, and then creating a pull request on a given github repo with the implemented changes. This agent collaborates with a group of specialized agents to handle the workflow efficiently.

[![Watch the video](images/coder.png)](https://www.youtube.com/watch?v=K2KUVdZjZnc)

### **Key Features**

- **Autonomous Feature Development**: Identifies potential improvements and new features for a codebase without user intervention.
- **Automated Workflow**: Handles the end-to-end process, including coding, review, and implementation.
- **GitHub Integration**: Creates pull requests directly on the specified GitHub repository.
- **Error Handling and Iterative Refinement**: Continuously tests and improves the code until it meets quality standards.

### **Workflow Breakdown**
Let's go over a workflow where an AI agent autonomously identifies potential new features, writes the necessary code, integrates it into the codebase, and submits a pull request to the GitHub repository.

A. **Codebase Backup**:

   - The user provides a GitHub access token and a github repository link. The AI creates a secure backup of the local codebase to ensure rollback options.

B. **Feature Identification**:

   - The **Product Manager Agent** analyzes the codebase and suggests potential new features.

C. **Feature Implementation**:

   - The **Software Engineer Agent** writes the code for the new feature.

D. **Code Review**:

   - The **Code Reviewer Agent** inspects the code for bugs, inefficiencies, and adherence to coding standards.

E. **Feature Integration**:

   - The **Section Manager Agent** integrates the new feature into the codebase.

F. **Testing and Deployment**:

   - Tests the implemented feature to ensure functionality.
   - Creates a pull request on the specified GitHub repository.

G. **Backup Restoration**:

   - Restores the original backup if errors arise during the process.

### **Example Use Case**

#### **User Query**:
"Analyze this codebase and implement a feature that tracks user activity and logs it into a database."

### **Teams of Agents**

A. **Product Manager Agent**:

   - Identifies the need for user activity tracking and creates a task description.

B. **Software Engineer Agent**:

   - Writes the Python code to track user activity and log it to a database.

C. **Code Reviewer Agent**:

   - Validates the code for potential bugs, inefficiencies, and adherence to best practices.

D. **Section Manager Agent**:

   - Integrates the new feature into the main codebase and creates a pull request.

### **Workflow**

#### **Step 1: Initial Query**
- **User Query**:
  "Create a Python script that scrapes data from a website, stores it in a CSV file, and optimizes the code for better performance."

- **User Input**:
  Provides a GitHub access token and repository URL.

#### **Step 2: Orchestrator Processing**
- The **Orchestrator** interprets the input and creates tasks:
  1. Analyze the codebase for new features.
  2. Implement the feature.
  3. Review, test, and deploy the feature.

#### **Step 3: Task Execution**

A. **Feature Analysis**:

   - **Product Manager Agent** scans the codebase and identifies user activity tracking as a valuable addition.

B. **Feature Implementation**:

   - **Software Engineer Agent** writes a Python function to log user activity into a database or simulate such logging.

C. **Code Review**:

   - **Code Reviewer Agent** checks for vulnerabilities, syntax errors, and performance inefficiencies.

D. **Integration**:

   - **Section Manager Agent** integrates the feature into the codebase and creates a pull request.

#### **Step 4: Testing and Iteration**
- Tests the feature for functionality and usability.
- If issues arise, tasks are reassigned to relevant agents for debugging and improvement.

#### **Step 5: Cycle Continues**
- The system iteratively improves the feature or script until it meets the desired performance and functionality standards.
