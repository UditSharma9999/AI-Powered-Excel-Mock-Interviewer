from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os
import uuid
import datetime
import json
import re
from typing import Dict, List, Optional
from langchain.memory import ConversationBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

app = Flask(__name__)
app.config['SECRET_KEY'] = 'excel-mock-interviewer-2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize the ChatGoogleGenerativeAI model
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)

class InterviewState:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.current_question = 0
        self.questions_asked = []
        self.responses = []
        self.scores = []
        self.start_time = datetime.datetime.now()
        self.is_active = False
        self.candidate_name = ""
        self.skill_level = "beginner"  # beginner, intermediate, advanced
        self.memory = ConversationBufferMemory(return_messages=True)
        self.generated_questions = []

interview_sessions: Dict[str, InterviewState] = {}

class ExcelInterviewAgent:
    def __init__(self):
        self.system_prompt = """
You are an experienced Excel interviewer conducting a professional mock interview. Your role is to:
1. Be conversational and encouraging while maintaining professionalism
2. Ask follow-up questions based on responses
3. Provide hints if a candidate is struggling (but note this in evaluation)
4. Evaluate technical accuracy and practical understanding
5. Score responses on a scale of 1-10
6. Generate constructive feedback

When evaluating responses, consider:
- Technical accuracy
- Practical understanding
- Communication clarity
- Real-world application knowledge

Respond in a natural, conversational way as a human interviewer would.
        """

    def generate_questions(self, skill_level: str, num_questions: int = 5) -> List[Dict]:
        """Generate Excel questions based on skill level using AI"""
        
        question_prompt = f"""
Generate {num_questions} Excel interview questions for {skill_level} level candidates.

For {skill_level} level, focus on:
- Beginner: Basic formulas, cell formatting, simple functions (SUM, AVERAGE), basic charts
- Intermediate: VLOOKUP, Pivot Tables, conditional formatting, intermediate functions, data validation
- Advanced: INDEX/MATCH, advanced functions, VBA basics, complex formulas, data analysis

Return the questions in this exact JSON format:
[
    {{
        "question": "Question text here",
        "topic": "Main topic (e.g., VLOOKUP, Pivot Tables, etc.)",
        "difficulty": 1-10,
        "weight": 5-15 (higher for more important topics)
    }}
]

Make questions practical and scenario-based. Each question should test real Excel skills that would be used in a workplace.
        """
        
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=question_prompt)
            ]
            
            result = model.invoke(messages)
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', result.content, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group())
                return questions
            else:
                # Fallback to default questions if AI generation fails
                return self._get_fallback_questions(skill_level)
                
        except Exception as e:
            print(f"Error generating questions: {e}")
            return self._get_fallback_questions(skill_level)

    def _get_fallback_questions(self, skill_level: str) -> List[Dict]:
        """Fallback questions in case AI generation fails"""
        fallback_questions = {
            "beginner": [
                {
                    "question": "What is Microsoft Excel and what is its primary purpose?",
                    "topic": "Excel Basics",
                    "difficulty": 2,
                    "weight": 5
                },
                {
                    "question": "How would you create a simple SUM formula in Excel?",
                    "topic": "Basic Formulas",
                    "difficulty": 3,
                    "weight": 6
                },
                {
                    "question": "Explain how to format a cell to display currency in Excel.",
                    "topic": "Cell Formatting",
                    "difficulty": 3,
                    "weight": 5
                },
                {
                    "question": "How do you create a basic chart in Excel?",
                    "topic": "Charts",
                    "difficulty": 4,
                    "weight": 7
                },
                {
                    "question": "What's the difference between relative and absolute cell references?",
                    "topic": "Cell References",
                    "difficulty": 5,
                    "weight": 8
                }
            ],
            "intermediate": [
                {
                    "question": "Explain how VLOOKUP function works and give me an example of when you'd use it.",
                    "topic": "VLOOKUP",
                    "difficulty": 6,
                    "weight": 10
                },
                {
                    "question": "How would you create and customize a Pivot Table?",
                    "topic": "Pivot Tables",
                    "difficulty": 7,
                    "weight": 12
                },
                {
                    "question": "Explain conditional formatting and give me a practical use case.",
                    "topic": "Conditional Formatting",
                    "difficulty": 5,
                    "weight": 7
                },
                {
                    "question": "How do you use data validation to create dropdown lists?",
                    "topic": "Data Validation",
                    "difficulty": 6,
                    "weight": 8
                },
                {
                    "question": "What are some ways to handle errors in Excel formulas?",
                    "topic": "Error Handling",
                    "difficulty": 7,
                    "weight": 9
                }
            ],
            "advanced": [
                {
                    "question": "How would you use INDEX and MATCH functions together, and why might this be better than VLOOKUP?",
                    "topic": "INDEX/MATCH",
                    "difficulty": 8,
                    "weight": 15
                },
                {
                    "question": "Explain how to create and use array formulas in Excel.",
                    "topic": "Array Formulas",
                    "difficulty": 9,
                    "weight": 12
                },
                {
                    "question": "How would you automate repetitive tasks in Excel using VBA?",
                    "topic": "VBA",
                    "difficulty": 9,
                    "weight": 15
                },
                {
                    "question": "Describe advanced data analysis techniques you can perform in Excel.",
                    "topic": "Data Analysis",
                    "difficulty": 8,
                    "weight": 13
                },
                {
                    "question": "How do you optimize Excel performance when working with large datasets?",
                    "topic": "Performance Optimization",
                    "difficulty": 8,
                    "weight": 10
                }
            ]
        }
        
        return fallback_questions.get(skill_level, fallback_questions["beginner"])

    def evaluate_response(self, question: str, response: str, topic: str, difficulty: int, weight: int) -> Dict:
        """Evaluate response using AI instead of keyword matching"""
        
        evaluation_prompt = f"""
As an Excel interviewer, evaluate this candidate's response to an Excel question.

Question: {question}
Topic: {topic}
Difficulty Level: {difficulty}/10
Candidate's Response: {response}

Evaluate the response based on:
1. Technical accuracy - Is the information correct?
2. Completeness - Does it fully answer the question?
3. Practical understanding - Do they understand real-world applications?
4. Communication clarity - Is the explanation clear and well-structured?
5. Depth of knowledge - Do they show understanding beyond basics?

Provide your evaluation in this exact JSON format:
{{
    "score": <number from 1-10>,
    "technical_accuracy": <number from 1-10>,
    "communication_clarity": <number from 1-10>,
    "completeness": <number from 1-10>,
    "practical_understanding": <number from 1-10>,
    "feedback": "<constructive feedback about their response>",
    "suggestions": "<specific suggestions for improvement>",
    "strengths": "<what they did well in their response>",
    "areas_for_improvement": "<specific areas that need work>"
}}

Scoring guidelines:
- 1-3: Poor/Incorrect response with major errors
- 4-5: Basic understanding but significant gaps or errors
- 6-7: Good understanding with minor gaps
- 8-9: Very good response with comprehensive understanding
- 10: Excellent, expert-level response

Be fair but thorough in your evaluation. Consider the difficulty level when scoring.
Be strict with scoring - wrong answers should get low scores (1-3).
        """
        
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=evaluation_prompt)
            ]
            
            result = model.invoke(messages)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result.content, re.DOTALL)
            if json_match:
                evaluation = json.loads(json_match.group())
                # Fix scoring calculation - use percentage of max possible for this question
                raw_score = evaluation['score']
                max_possible_for_question = 10  # Each question is scored out of 10
                percentage_score = (raw_score / max_possible_for_question) * weight
                
                evaluation['raw_score'] = raw_score
                evaluation['weighted_score'] = percentage_score
                evaluation['max_possible'] = weight
                evaluation['topic'] = topic
                evaluation['difficulty'] = difficulty
                return evaluation
            else:
                # Fallback scoring if JSON parsing fails
                return self._fallback_evaluation(response, weight, topic, difficulty)
                
        except Exception as e:
            print(f"Error evaluating response: {e}")
            return self._fallback_evaluation(response, weight, topic, difficulty)

    def _fallback_evaluation(self, response: str, weight: int, topic: str, difficulty: int) -> Dict:
        """Fallback evaluation when AI evaluation fails"""
        # Simple length and content-based scoring
        response_length = len(response.split())
        if response_length < 3:
            base_score = 1  # Very short responses get low scores
        elif response_length < 10:
            base_score = 3
        elif response_length < 20:
            base_score = 5
        else:
            base_score = 6  # Cap at 6 for fallback method
        
        # Calculate weighted score properly
        max_possible_for_question = 10
        percentage_score = (base_score / max_possible_for_question) * weight
        
        return {
            "score": base_score,
            "raw_score": base_score,
            "technical_accuracy": base_score,
            "communication_clarity": min(10, base_score + 1),
            "completeness": max(1, base_score - 1),
            "practical_understanding": base_score,
            "feedback": "Response evaluated using fallback method. AI evaluation temporarily unavailable.",
            "suggestions": f"Try to provide more detailed explanations about {topic}.",
            "strengths": "Response provided within time limit.",
            "areas_for_improvement": "Consider providing more technical details and practical examples.",
            "weighted_score": percentage_score,
            "max_possible": weight,
            "topic": topic,
            "difficulty": difficulty
        }

    def get_next_question(self, state: InterviewState) -> Optional[Dict]:
        """Get the next question for the interview"""
        if state.current_question >= len(state.generated_questions):
            return None
        return state.generated_questions[state.current_question]

    def generate_final_report(self, state: InterviewState) -> Dict:
        """Generate comprehensive final report using AI analysis"""
        if not state.scores:
            return {"error": "No responses to evaluate"}

        # Calculate scores properly
        total_weighted_score = sum(score.get('weighted_score', 0) for score in state.scores)
        total_max_possible = sum(score.get('max_possible', 0) for score in state.scores)
        
        # Calculate percentage correctly
        percentage = (total_weighted_score / total_max_possible * 100) if total_max_possible > 0 else 0
        
        # Ensure percentage cannot exceed 100%
        percentage = min(percentage, 100.0)

        # Calculate average raw score for proficiency determination
        raw_scores = [score.get('raw_score', score.get('score', 0)) for score in state.scores]
        avg_raw_score = sum(raw_scores) / len(raw_scores) if raw_scores else 0

        # Determine proficiency level based on average raw score (1-10 scale)
        if avg_raw_score >= 8.5:
            proficiency = "Advanced"
        elif avg_raw_score >= 7.0:
            proficiency = "Intermediate" 
        elif avg_raw_score >= 5.5:
            proficiency = "Basic"
        else:
            proficiency = "Beginner"

        # Generate AI-powered overall assessment
        overall_feedback = self._generate_ai_feedback(state.scores, percentage, state.skill_level)
        recommendations = self._generate_ai_recommendations(state.scores, percentage, state.skill_level)

        return {
            "candidate_name": state.candidate_name,
            "skill_level": state.skill_level,
            "total_score": round(total_weighted_score, 1),
            "max_possible_score": total_max_possible,
            "percentage": round(percentage, 1),
            "average_raw_score": round(avg_raw_score, 1),
            "proficiency_level": proficiency,
            "questions_answered": len(state.responses),
            "interview_duration": str(datetime.datetime.now() - state.start_time),
            "detailed_scores": state.scores,
            "overall_feedback": overall_feedback,
            "recommendations": recommendations,
            "topic_breakdown": self._analyze_topic_performance(state.scores)
        }

    def _generate_ai_feedback(self, scores: List[Dict], percentage: float, skill_level: str) -> str:
        """Generate overall feedback using AI"""
        
        # Prepare score summary for AI
        score_summary = []
        for i, score in enumerate(scores):
            score_summary.append({
                "question_num": i + 1,
                "topic": score.get('topic', 'Unknown'),
                "score": score.get('score', 0),
                "technical_accuracy": score.get('technical_accuracy', 0),
                "strengths": score.get('strengths', ''),
                "areas_for_improvement": score.get('areas_for_improvement', '')
            })

        feedback_prompt = f"""
Analyze this Excel interview performance and provide overall feedback.

Candidate Level: {skill_level}
Overall Percentage: {percentage:.1f}%
Number of Questions: {len(scores)}

Question-by-question performance:
{json.dumps(score_summary, indent=2)}

Provide a comprehensive but concise overall feedback (2-3 sentences) that:
1. Acknowledges their overall performance level
2. Highlights key strengths observed across questions
3. Identifies the most important areas for improvement
4. Is encouraging but honest

Write in a professional, supportive tone as an interviewer would.
        """
        
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=feedback_prompt)
            ]
            
            result = model.invoke(messages)
            return result.content.strip()
            
        except Exception as e:
            # Fallback feedback
            if percentage >= 85:
                return "Excellent performance! You demonstrate strong Excel proficiency across multiple areas."
            elif percentage >= 70:
                return "Good performance with solid Excel knowledge. Some areas could benefit from additional practice."
            elif percentage >= 55:
                return "Basic understanding demonstrated. Focus on expanding your Excel skills through targeted practice."
            else:
                return "Foundational Excel concepts need development. Consider structured learning to build core skills."

    def _generate_ai_recommendations(self, scores: List[Dict], percentage: float, skill_level: str) -> List[str]:
        """Generate personalized recommendations using AI"""
        
        # Analyze weak areas
        weak_topics = []
        for score in scores:
            if score.get('score', 0) < 6:
                weak_topics.append(score.get('topic', 'Unknown'))
        
        recommendations_prompt = f"""
Based on this Excel interview performance, provide 3-5 specific, actionable learning recommendations.

Skill Level Tested: {skill_level}
Overall Score: {percentage:.1f}%
Weak Areas Identified: {', '.join(weak_topics) if weak_topics else 'None major'}

Performance Summary:
{json.dumps([{'topic': s.get('topic'), 'score': s.get('score')} for s in scores], indent=2)}

Provide specific, actionable recommendations as a JSON array:
["recommendation 1", "recommendation 2", "recommendation 3", ...]

Focus on:
1. Addressing identified weak areas
2. Building on strengths
3. Practical learning resources or methods
4. Progressive skill development
5. Real-world application practice

Keep recommendations concise and actionable.
        """
        
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=recommendations_prompt)
            ]
            
            result = model.invoke(messages)
            
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', result.content, re.DOTALL)
            if json_match:
                recommendations = json.loads(json_match.group())
                return recommendations
            else:
                return self._fallback_recommendations(percentage, skill_level, weak_topics)
                
        except Exception as e:
            return self._fallback_recommendations(percentage, skill_level, weak_topics)

    def _fallback_recommendations(self, percentage: float, skill_level: str, weak_topics: List[str]) -> List[str]:
        """Fallback recommendations when AI generation fails"""
        recommendations = []
        
        if percentage < 70:
            recommendations.append("Practice basic Excel formulas and functions daily")
            recommendations.append("Take an online Excel fundamentals course")
        
        if weak_topics:
            recommendations.append(f"Focus on improving skills in: {', '.join(set(weak_topics))}")
        
        if skill_level in ['intermediate', 'advanced'] and percentage < 85:
            recommendations.append("Master advanced lookup functions (VLOOKUP, INDEX/MATCH)")
            recommendations.append("Practice creating and analyzing Pivot Tables")
        
        if skill_level == 'advanced' and percentage < 90:
            recommendations.append("Learn VBA for automation")
            recommendations.append("Explore advanced data analysis techniques")
        
        recommendations.append("Consider pursuing Microsoft Excel certification")
        
        return recommendations[:5]  # Limit to 5 recommendations

    def _analyze_topic_performance(self, scores: List[Dict]) -> Dict:
        """Analyze performance by topic area"""
        topic_scores = {}
        
        for score in scores:
            topic = score.get('topic', 'Unknown')
            if topic not in topic_scores:
                topic_scores[topic] = []
            topic_scores[topic].append(score.get('score', 0))
        
        topic_analysis = {}
        for topic, topic_score_list in topic_scores.items():
            avg_score = sum(topic_score_list) / len(topic_score_list)
            topic_analysis[topic] = {
                'average_score': round(avg_score, 1),
                'questions_count': len(topic_score_list),
                'performance_level': 'Strong' if avg_score >= 7 else 'Moderate' if avg_score >= 5 else 'Needs Improvement'
            }
        
        return topic_analysis

interview_agent = ExcelInterviewAgent()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def on_disconnect():
    print(f'Client disconnected: {request.sid}')

@socketio.on('start_interview')
def handle_start_interview(data):
    session_id = request.sid
    candidate_name = data.get('name', 'Candidate')
    skill_level = data.get('skill_level', 'beginner')

    state = InterviewState()
    state.candidate_name = candidate_name
    state.skill_level = skill_level
    state.is_active = True
    
    # Generate questions using AI
    state.generated_questions = interview_agent.generate_questions(skill_level, num_questions=5)
    
    interview_sessions[session_id] = state
    
    if state.generated_questions:
        first_question = state.generated_questions[0]
        welcome_message = f"Hello {candidate_name}! Welcome to your Excel mock interview. I'll be asking you {len(state.generated_questions)} questions about Excel at the {skill_level} level. Let's begin with our first question: {first_question['question']}"

        emit('interview_started', {
            'message': welcome_message,
            'question_number': 1,
            'total_questions': len(state.generated_questions)
        })
    else:
        emit('error', {'message': 'Could not generate interview questions'})

@socketio.on('submit_response')
def handle_response(data):
    """Handle candidate response and evaluate using AI"""
    session_id = request.sid
    response_text = data.get('response', '')
    
    if session_id not in interview_sessions:
        emit('error', {'message': 'No active interview session'})
        return
    
    state = interview_sessions[session_id]
    if not state.is_active:
        emit('error', {'message': 'Interview is not active'})
        return

    if state.current_question >= len(state.generated_questions):
        emit('error', {'message': 'No more questions available'})
        return

    current_q = state.generated_questions[state.current_question]

    # Store response
    state.responses.append({
        'question': current_q['question'],
        'response': response_text,
        'timestamp': datetime.datetime.now()
    })

    # Evaluate response using AI
    evaluation = interview_agent.evaluate_response(
        current_q['question'],
        response_text,
        current_q['topic'],
        current_q['difficulty'],
        current_q['weight']
    )

    state.scores.append(evaluation)
    state.current_question += 1

    # Check if interview is complete
    if state.current_question >= len(state.generated_questions):
        final_report = interview_agent.generate_final_report(state)
        state.is_active = False
        emit('interview_complete', {
            'report': final_report,
            'message': "Congratulations! You've completed the Excel mock interview. Here's your detailed performance report."
        })
    else:
        next_question = state.generated_questions[state.current_question]
        emit('next_question', {
            'question': next_question['question'],
            'question_number': state.current_question + 1,
            'total_questions': len(state.generated_questions),
            'feedback': evaluation.get('feedback', ''),
            'score': evaluation.get('score', 0)
        })

@socketio.on('end_interview')
def handle_end_interview():
    session_id = request.sid
    if session_id in interview_sessions:
        state = interview_sessions[session_id]
        if state.responses:  # If at least one question was answered
            final_report = interview_agent.generate_final_report(state)
            emit('interview_complete', {
                'report': final_report,
                'message': "Interview ended early. Here's your performance report based on the questions you answered."
            })
        else:
            emit('interview_ended', {'message': 'Interview ended. No responses to evaluate.'})
        state.is_active = False

if __name__ == '__main__':
    print("use: http://localhost:5000")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)