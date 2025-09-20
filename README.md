
# AI-Powered Excel Mock Interviewer

## 1. Project Overview
The AI-Powered Excel Mock Interviewer aims to automate technical interviews by simulating real interview scenarios focused on Excel skills. The system evaluates candidate answers using AI for technical accuracy, communication, completeness, and practical understanding.

## 2. Technology Stack
- **Backend**: Flask with SocketIO for real-time interaction
- **Frontend**: HTML, CSS, JavaScript (with voice recognition and synthesis)
- **AI Engine**: Google Generative AI via LangChain for question generation, response evaluation, and feedback
- **State Management**: In-memory session with persistent question and answer state using a dedicated InterviewState class

## 3. Core Functionalities
- **Interview Setup**: Candidate inputs name and Excel skill level (beginner, intermediate, advanced)
- **Dynamic Interview Flow**: Questions are delivered one at a time, responses received and evaluated asynchronously
- **Answer Evaluation**: AI evaluates responses on a 1-10 scale across multiple dimensions
- **Agentic Interaction**: The system maintains context, provides encouragement, and adapts feedback
- **Final Report**: A detailed summary with scores, proficiency level, topic breakdown, and recommendations

## 4. Architecture Diagram
```plaintext
Client (Browser)
   |
SocketIO
   |
Flask Server
   |
LangChain -> Google Generative AI (Gemini)

State: InterviewState handles session, questions, responses, scores
```

## 5. Challenges and Solutions
- Handling dynamic conversational flow: Managed via SocketIO events and state tracking
- Reliable AI evaluation: Used prompt engineering and JSON parsing to standardize scores
- Speech integration: Leveraged Web Speech API for voice input/output

## 6. Future Enhancements
- Real-time dynamic follow-ups based on answers
- Transcript generation and export as PDF
- More nuanced scoring with rubrics
- Scalability improvements with database backing

## 7. Repository and Deployment
- Includes complete runnable source code (app.py, app.js, index.html, styles.css)
- Setup and run instructions provided in README (assumed)
- Deployment on a cloud platform (Heroku, AWS, etc.) recommended for easy access

<!-- ## 8. Sample Interview Transcripts
Also included sample transcripts showcasing the system's evaluation and feedback abilities. -->
 
-----

# Quick Start

## Prerequisites
- Python 3.8 or higher
- Google AI API key (Gemini)

## Setup Instructions

## 1. Create and activate virtual environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

## 2. Install dependencies
```pip install -r requirements.txt ```


## 3. Set up environment variables

Create a .env file in the root directory:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

Or set the environment variable directly in your terminal:

```bash
# On Windows:
set GOOGLE_API_KEY=your_google_api_key_here

# On macOS/Linux:
export GOOGLE_API_KEY=your_google_api_key_here
```

## 4. Run the application
```python app.py```

### 5. Access the application

> Open your browser and navigate to: http://localhost:5000


