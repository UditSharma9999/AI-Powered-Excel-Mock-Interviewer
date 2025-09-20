class ExcelInterviewer {
    constructor() {
        this.socket = io();
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isRecording = false;
        this.currentTranscript = '';
        this.microphoneReady = false;

        this.initializeEventListeners();
        this.initializeSpeechRecognition();
        this.initializeSocketListeners();
    }

    initializeEventListeners() {
        // Setup form
        document.getElementById('setup-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startInterview();
        });

        // Microphone test
        document.getElementById('test-mic').addEventListener('click', () => {
            this.testMicrophone();
        });

        // Voice controls
        document.getElementById('start-recording').addEventListener('click', () => {
            this.startRecording();
        });

        document.getElementById('stop-recording').addEventListener('click', () => {
            this.stopRecording();
        });

        // Action buttons
        document.getElementById('submit-response').addEventListener('click', () => {
            this.submitResponse();
        });

        document.getElementById('skip-question').addEventListener('click', () => {
            this.skipQuestion();
        });

        document.getElementById('end-interview').addEventListener('click', () => {
            this.endInterview();
        });

        // Results actions
        document.getElementById('download-report').addEventListener('click', () => {
            this.downloadReport();
        });

        document.getElementById('start-new-interview').addEventListener('click', () => {
            this.startNewInterview();
        });
    }

    initializeSpeechRecognition() {
        // Check for browser support
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            this.showError('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onstart = () => {
            console.log('Speech recognition started');
            this.updateUIForRecording(true);
        };

        this.recognition.onresult = (event) => {
            let interim = '';
            let final = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    final += transcript;
                } else {
                    interim += transcript;
                }
            }

            this.currentTranscript = final;
            this.updateTranscription(final + interim);
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.handleRecognitionError(event.error);
        };

        this.recognition.onend = () => {
            console.log('Speech recognition ended');
            this.updateUIForRecording(false);
        };
    }

    initializeSocketListeners() {
        this.socket.on('connect', () => {
            console.log('Connected to server');
        });

        this.socket.on('interview_started', (data) => {
            this.handleInterviewStarted(data);
        });

        this.socket.on('next_question', (data) => {
            this.handleNextQuestion(data);
        });

        this.socket.on('interview_complete', (data) => {
            this.handleInterviewComplete(data);
        });

        this.socket.on('error', (data) => {
            this.showError(data.message);
        });
    }

    async testMicrophone() {
        const button = document.getElementById('test-mic');
        const status = document.getElementById('mic-status');

        button.disabled = true;
        button.textContent = 'Testing...';

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            status.innerHTML = '<span style="color: green;">✅ Microphone is working!</span>';
            this.microphoneReady = true;
            document.getElementById('start-interview').disabled = false;

            // Stop the stream
            stream.getTracks().forEach(track => track.stop());
        } catch (error) {
            status.innerHTML = '<span style="color: red;">❌ Microphone access denied or not available</span>';
            this.microphoneReady = false;
        } finally {
            button.disabled = false;
            button.textContent = 'Test Microphone';
        }
    }

    startInterview() {
        const name = document.getElementById('candidate-name').value;
        const skillLevel = document.getElementById('skill-level').value;

        if (!name || !skillLevel || !this.microphoneReady) {
            this.showError('Please fill in all fields and test your microphone first.');
            return;
        }

        // Emit start interview event
        this.socket.emit('start_interview', {
            name: name,
            skill_level: skillLevel
        });
    }

    handleInterviewStarted(data) {
        // Switch to interview phase
        this.switchPhase('interview-phase');

        // Update UI
        this.updateProgress(data.question_number, data.total_questions);
        this.updateQuestion(data.message);
        this.speakText(data.message);

        // Show success message
        this.showSuccess('Interview started! Listen to the question and click "Click to Answer" when ready.');
    }

    handleNextQuestion(data) {
        // Update progress
        this.updateProgress(data.question_number, data.total_questions);

        // Show feedback from previous question
        if (data.feedback) {
            this.showFeedback(data.feedback, data.score);
        }

        // Update question
        this.updateQuestion(data.question);
        this.speakText(data.question);

        // Reset UI
        this.resetResponseUI();
    }

    handleInterviewComplete(data) {
        // Switch to results phase
        this.switchPhase('results-phase');

        // Display results
        this.displayResults(data.report);

        // Speak completion message
        this.speakText(data.message);

        this.showSuccess('Interview completed successfully!');
    }

    startRecording() {
        if (!this.recognition) {
            this.showError('Speech recognition not available');
            return;
        }

        this.isRecording = true;
        this.currentTranscript = '';
        this.updateTranscription('Listening...');

        try {
            this.recognition.start();
        } catch (error) {
            this.handleRecognitionError(error.message);
        }
    }

    stopRecording() {
        if (this.recognition && this.isRecording) {
            this.recognition.stop();
            this.isRecording = false;
        }
    }

    submitResponse() {
        if (!this.currentTranscript.trim()) {
            this.showError('Please record your response first.');
            return;
        }

        // Emit response to server
        this.socket.emit('submit_response', {
            response: this.currentTranscript
        });

        // Update UI
        document.getElementById('submit-response').disabled = true;
        document.getElementById('submit-response').textContent = 'Processing...';

        this.showInfo('Processing your response...');
    }

    skipQuestion() {
        if (confirm('Are you sure you want to skip this question? This will count as an unanswered question.')) {
            this.socket.emit('submit_response', {
                response: 'Question skipped by candidate'
            });
        }
    }

    endInterview() {
        if (confirm('Are you sure you want to end the interview? You can review your results for completed questions.')) {
            this.socket.emit('end_interview');
        }
    }

    // UI Helper Methods
    switchPhase(phaseId) {
        // Hide all phases
        document.querySelectorAll('.phase').forEach(phase => {
            phase.classList.remove('active');
        });

        // Show target phase
        document.getElementById(phaseId).classList.add('active');
    }

    updateProgress(current, total) {
        const percentage = (current / total) * 100;
        document.getElementById('progress-fill').style.width = percentage + '%';
        document.getElementById('progress-text').textContent = `Question ${current} of ${total}`;
    }

    updateQuestion(question) {
        document.getElementById('current-question').textContent = question;
    }

    updateTranscription(text) {
        const transcriptionBox = document.getElementById('transcription');
        transcriptionBox.textContent = text;
        transcriptionBox.classList.add('active');

        if (text && text !== 'Listening...') {
            document.getElementById('submit-response').disabled = false;
        }
    }

    updateUIForRecording(recording) {
        const startBtn = document.getElementById('start-recording');
        const stopBtn = document.getElementById('stop-recording');

        if (recording) {
            startBtn.classList.add('hidden');
            stopBtn.classList.remove('hidden');
            stopBtn.disabled = false;
            startBtn.classList.add('recording');
        } else {
            startBtn.classList.remove('hidden');
            stopBtn.classList.add('hidden');
            startBtn.classList.remove('recording');
            this.isRecording = false;
        }
    }

    resetResponseUI() {
        this.currentTranscript = '';
        this.updateTranscription('Your response will appear here...');
        document.getElementById('submit-response').disabled = true;
        document.getElementById('submit-response').textContent = 'Submit Response';
        document.getElementById('transcription').classList.remove('active');

        // Hide previous feedback
        document.getElementById('feedback-section').classList.add('hidden');
    }

    showFeedback(feedback, score) {
        const feedbackSection = document.getElementById('feedback-section');
        const feedbackContent = document.getElementById('question-feedback');

        feedbackContent.innerHTML = `
            <div class="feedback-score">Score: ${score}/10</div>
            <div class="feedback-text">${feedback}</div>
        `;

        feedbackSection.classList.remove('hidden');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            feedbackSection.classList.add('hidden');
        }, 5000);
    }

    displayResults(report) {
        const resultsContent = document.getElementById('results-content');

        // Determine proficiency class
        let proficiencyClass = 'proficiency-beginner';
        if (report.proficiency_level === 'Advanced') proficiencyClass = 'proficiency-advanced';
        else if (report.proficiency_level === 'Intermediate') proficiencyClass = 'proficiency-intermediate';
        else if (report.proficiency_level === 'Basic') proficiencyClass = 'proficiency-basic';

        resultsContent.innerHTML = `
            <div class="results-summary">
                <h3>Interview Results for ${report.candidate_name}</h3>
                <div class="score-display">${report.percentage}%</div>
                <div class="proficiency-level ${proficiencyClass}">
                    ${report.proficiency_level} Level
                </div>
                <p><strong>Skill Level Tested:</strong> ${report.skill_level.toUpperCase()}</p>
                <p><strong>Questions Answered:</strong> ${report.questions_answered}</p>
                <p><strong>Duration:</strong> ${report.interview_duration}</p>
            </div>

            <div class="results-details">
                <h4>Overall Feedback</h4>
                <p>${report.overall_feedback}</p>

                <div class="score-breakdown">
                    <div class="score-item">
                        <div class="score-value">${report.total_score}</div>
                        <div>Total Score</div>
                    </div>
                    <div class="score-item">
                        <div class="score-value">${report.max_possible_score}</div>
                        <div>Max Possible</div>
                    </div>
                    <div class="score-item">
                        <div class="score-value">${report.percentage}%</div>
                        <div>Performance</div>
                    </div>
                </div>

                ${this.generateDetailedScores(report.detailed_scores)}

                ${report.recommendations.length > 0 ? `
                <div class="recommendations">
                    <h4>📚 Learning Recommendations</h4>
                    <ul>
                        ${report.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}
            </div>
        `;

        // Store report for download
        this.currentReport = report;
    }

    generateDetailedScores(scores) {
        if (!scores || scores.length === 0) return '';

        return `
            <h4>Question-by-Question Breakdown</h4>
            ${scores.map((score, index) => `
                <div class="question-result">
                    <h5>Question ${index + 1}</h5>
                    <div class="score-breakdown">
                        <div class="score-item">
                            <div class="score-value">${score.score || 0}</div>
                            <div>Overall Score</div>
                        </div>
                        <div class="score-item">
                            <div class="score-value">${score.technical_accuracy || 0}</div>
                            <div>Technical</div>
                        </div>
                        <div class="score-item">
                            <div class="score-value">${score.communication_clarity || 0}</div>
                            <div>Communication</div>
                        </div>
                    </div>
                    <p><strong>Feedback:</strong> ${score.feedback || 'No feedback available'}</p>
                    ${score.suggestions ? `<p><strong>Suggestions:</strong> ${score.suggestions}</p>` : ''}
                </div>
            `).join('')}
        `;
    }

    downloadReport() {
        if (!this.currentReport) {
            this.showError('No report available to download');
            return;
        }

        const reportData = {
            ...this.currentReport,
            generated_date: new Date().toISOString(),
            application: 'AI-Powered Excel Mock Interviewer'
        };

        const blob = new Blob([JSON.stringify(reportData, null, 2)], {
            type: 'application/json'
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `excel-interview-report-${this.currentReport.candidate_name}-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.showSuccess('Report downloaded successfully!');
    }

    startNewInterview() {
        if (confirm('This will start a completely new interview. Continue?')) {
            location.reload();
        }
    }

    // Text-to-Speech
    speakText(text) {
        if (this.synthesis && this.synthesis.speak) {
            // Stop any ongoing speech
            this.synthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            utterance.pitch = 1;
            utterance.volume = 0.8;

            // Try to use a pleasant voice
            const voices = this.synthesis.getVoices();
            const preferredVoice = voices.find(voice => 
                voice.name.includes('Female') || voice.name.includes('Samantha') || voice.name.includes('Karen')
            );
            if (preferredVoice) {
                utterance.voice = preferredVoice;
            }

            this.synthesis.speak(utterance);
        }
    }

    // Error handling
    handleRecognitionError(error) {
        let message = 'Speech recognition error occurred.';

        switch (error) {
            case 'no-speech':
                message = 'No speech detected. Please try again.';
                break;
            case 'audio-capture':
                message = 'Audio capture failed. Check your microphone.';
                break;
            case 'not-allowed':
                message = 'Microphone access denied. Please allow microphone access.';
                break;
            case 'network':
                message = 'Network error occurred. Check your internet connection.';
                break;
        }

        this.showError(message);
        this.updateUIForRecording(false);
    }

    // Notification methods
    showError(message) {
        this.showNotification(message, 'error');
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showInfo(message) {
        this.showNotification(message, 'info');
    }

    showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">
                    ${type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'}
                </span>
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;

        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#f8d7da' : type === 'success' ? '#d4edda' : '#d1ecf1'};
            color: ${type === 'error' ? '#721c24' : type === 'success' ? '#155724' : '#0c5460'};
            border: 1px solid ${type === 'error' ? '#f5c6cb' : type === 'success' ? '#c3e6cb' : '#bee5eb'};
            border-radius: 8px;
            padding: 15px;
            max-width: 400px;
            z-index: 10000;
            animation: slideInRight 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

// Add notification styles to head
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    .notification-content {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .notification-close {
        background: none;
        border: none;
        font-size: 18px;
        cursor: pointer;
        padding: 0;
        margin-left: auto;
    }
`;
document.head.appendChild(notificationStyles);

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ExcelInterviewer();
});
