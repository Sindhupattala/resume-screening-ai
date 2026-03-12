// Global variables
let currentPage = 1;
const itemsPerPage = 3;
let resumeFiles = [];
let jdFile = null;
let currentMethod = 'text';
let candidatesData = [];

// DOM elements
const greetingElement = document.getElementById('greeting');
const jobDescriptionTextarea = document.getElementById('jobDescription');
const thresholdSlider = document.getElementById('threshold');
const thresholdValue = document.getElementById('threshold-value');
const resumeUploadArea = document.getElementById('resume-upload-area');
const resumeFileInput = document.getElementById('resume-file-input');
const resumeFileList = document.getElementById('resume-file-list');
const jdUploadArea = document.getElementById('jd-upload-area');
const jdFileInput = document.getElementById('jd-file-input');
const jdFileList = document.getElementById('jd-file-list');
const processButton = document.getElementById('process-button');
const loadingSpinner = document.querySelector('.loading-spinner');
const messageArea = document.getElementById('message-area');
const resultsSection = document.getElementById('results-section');
const candidatesContainer = document.getElementById('candidates-container');
const resumeModal = document.getElementById('resume-modal');
const resumeContent = document.getElementById('resume-content');
const resumeModalTitle = document.getElementById('resume-modal-title');





function parseMandatorySkills(rawText) {
    const result = {
        score: 'N/A',
        jdSkills: [],
        matched: [],
        missing: []
    };

    if (!rawText || typeof rawText !== 'string') {
        console.warn('Invalid mandatory_skills input:', rawText);
        return result;
    }

    console.log('Parsing mandatory_skills:', rawText); // Debug log

    try {
        const scoreMatch = rawText.match(/^([\d.]+\/[\d.]+)/i);
        if (scoreMatch) result.score = scoreMatch[1].replace(/\.$/, '');

        const jdSkillsMatch = rawText.match(/JD Skills: \[(.*?)\]/i);
        if (jdSkillsMatch && jdSkillsMatch[1]) {
            result.jdSkills = jdSkillsMatch[1].split(', ').filter(skill => skill.trim());
        }

        const matchedMatch = rawText.match(/Matched: \[(.*?)\]/i);
        if (matchedMatch && matchedMatch[1]) {
            result.matched = matchedMatch[1].split(', ').filter(skill => skill.trim());
        }

        const missingMatch = rawText.match(/Missing: \[(.*?)\]/i);
        if (missingMatch && missingMatch[1]) {
            result.missing = missingMatch[1].split(', ').filter(skill => skill.trim());
        }
    } catch (e) {
        console.error('Error parsing mandatory skills:', e, 'Raw text:', rawText);
        result.error = 'Failed to parse mandatory skills';
    }

    return result;
}

function parseTotalExperience(rawText) {
    const result = {
        score: 'N/A',
        employmentPeriods: [],
        totalMonths: '',
        years: '',
        jdRequirement: ''
    };

    if (!rawText || typeof rawText !== 'string') {
        console.warn('Invalid total_experience input:', rawText);
        return result;
    }

    console.log('Parsing total_experience:', rawText); // Debug log

    try {
        const scoreMatch = rawText.match(/^([\d.]+\/[\d.]+)/i);
        if (scoreMatch) result.score = scoreMatch[1].replace(/\.$/, '');

        const periodsMatch = rawText.match(/Employment periods: \[(.*?)\]/i);
        if (periodsMatch && periodsMatch[1]) {
            result.employmentPeriods = periodsMatch[1].split(', ').filter(period => period.trim());
        }

        const monthsMatch = rawText.match(/Total months after overlap removal: (\d+) months = ([\d.]+) years/i);
        if (monthsMatch) {
            result.totalMonths = monthsMatch[1];
            result.years = monthsMatch[2];
        }

        const jdMatch = rawText.match(/JD requirement: ([\d.]+) years/i);
        if (jdMatch) result.jdRequirement = jdMatch[1];
    } catch (e) {
        console.error('Error parsing total experience:', e, 'Raw text:', rawText);
        result.error = 'Failed to parse total experience';
    }

    return result;
}

function parseRelevantExperience(rawText) {
    const result = {
        score: 'N/A',
        relevantPeriods: [],
        totalMonths: '',
        years: '',
        jdRequirement: '',
        threshold: ''
    };

    if (!rawText || typeof rawText !== 'string') {
        console.warn('Invalid relevant_experience input:', rawText);
        return result;
    }

    console.log('Parsing relevant_experience:', rawText); // Debug log

    try {
        const scoreMatch = rawText.match(/^([\d.]+\/[\d.]+)/i);
        if (scoreMatch) result.score = scoreMatch[1].replace(/\.$/, '');

        const periodsMatch = rawText.match(/Relevant periods: \[(.*?)\]/i);
        if (periodsMatch && periodsMatch[1]) {
            result.relevantPeriods = periodsMatch[1].split(', ').filter(period => period.trim());
        }

        const monthsMatch = rawText.match(/Relevant months after overlap removal: (\d+) months = ([\d.]+) years/i);
        if (monthsMatch) {
            result.totalMonths = monthsMatch[1];
            result.years = monthsMatch[2];
        }

        const jdMatch = rawText.match(/JD requirement: ([\d.]+) years/i);
        if (jdMatch) result.jdRequirement = jdMatch[1];

        const thresholdMatch = rawText.match(/Threshold: ([\d.]+) year/i);
        if (thresholdMatch) result.threshold = thresholdMatch[1];
    } catch (e) {
        console.error('Error parsing relevant experience:', e, 'Raw text:', rawText);
        result.error = 'Failed to parse relevant experience';
    }

    return result;
}

function parseProjectExposure(rawText) {
    const result = {
        score: 'N/A',
        e2eProjects: [],
        supportProjects: [],
        academicUnrelated: [],
        scoringLogic: ''
    };

    if (!rawText || typeof rawText !== 'string') {
        console.warn('Invalid project_exposure input:', rawText);
        return result;
    }

    console.log('Parsing project_exposure:', rawText); // Debug log

    try {
        const scoreMatch = rawText.match(/^([\d.]+\/[\d.]+)/i);
        if (scoreMatch) result.score = scoreMatch[1].replace(/\.$/, '');

        const e2eMatch = rawText.match(/E2E projects: \[(.*?)\]/i);
        if (e2eMatch && e2eMatch[1]) {
            result.e2eProjects = e2eMatch[1].split(', ').filter(project => project.trim());
        }

        const supportMatch = rawText.match(/Support projects: \[(.*?)\]/i);
        if (supportMatch && supportMatch[1]) {
            result.supportProjects = supportMatch[1].split(', ').filter(project => project.trim());
        }

        const academicMatch = rawText.match(/Academic\/Unrelated: \[(.*?)\]/i);
        if (academicMatch && academicMatch[1]) {
            result.academicUnrelated = academicMatch[1].split(', ').filter(project => project.trim());
        }

        const scoringMatch = rawText.match(/Scoring logic: (.*?)$/i);
        if (scoringMatch) result.scoringLogic = scoringMatch[1];
    } catch (e) {
        console.error('Error parsing project exposure:', e, 'Raw text:', rawText);
        result.error = 'Failed to parse project exposure';
    }

    return result;
}







// Initialize
document.addEventListener('DOMContentLoaded', function() {
    updateGreeting();
    setupEventListeners();
    updateProcessButton();
});

function updateGreeting() {
    // Current time is 02:29 AM IST on July 27, 2025
    const hour = new Date('2025-07-27T02:29:00+05:30').getUTCHours() + 5.5; // Adjust for IST
    let greeting;
    if (hour >= 5 && hour < 12) {
        greeting = 'Good Morning';
    } else if (hour >= 12 && hour < 17) {
        greeting = 'Good Afternoon';
    } else {
        greeting = 'Good Evening';
    }
    greetingElement.textContent = greeting;
}

function setupEventListeners() {
    document.querySelectorAll('.method-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const method = this.dataset.method;
            switchMethod(method);
        });
    });

    thresholdSlider.addEventListener('input', function() {
        thresholdValue.textContent = this.value;
    });

    setupFileUpload(resumeUploadArea, resumeFileInput, handleResumeFiles);
    setupFileUpload(jdUploadArea, jdFileInput, handleJDFile);

    processButton.addEventListener('click', processCandidates);

    jobDescriptionTextarea.addEventListener('input', updateProcessButton);

    resumeModal.addEventListener('click', function(event) {
        if (event.target === resumeModal) {
            closeResumeModal();
        }
    });
}

function switchMethod(method) {
    currentMethod = method;

    document.querySelectorAll('.method-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-method="${method}"]`).classList.add('active');

    document.getElementById('text-method').style.display = method === 'text' ? 'block' : 'none';
    document.getElementById('file-method').style.display = method === 'file' ? 'block' : 'none';

    updateProcessButton();
}

function setupFileUpload(uploadArea, fileInput, handleFunction) {
    uploadArea.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFunction);

    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('drag-over');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
        const files = Array.from(e.dataTransfer.files);
        handleFunction({ target: { files } });
    });
}

function handleResumeFiles(event) {
    const files = Array.from(event.target.files);

    files.forEach(file => {
        if (isValidFile(file)) {
            resumeFiles.push(file);
        }
    });

    currentPage = 1;
    updateResumeFileList();
    updateProcessButton();
}

function handleJDFile(event) {
    const file = event.target.files[0];
    if (file && isValidFile(file)) {
        jdFile = file;
        updateJDFileList();
        updateProcessButton();
    }
}

function isValidFile(file) {
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    const maxSize = 10 * 1024 * 1024; // 10MB

    if (!allowedTypes.includes(file.type)) {
        showMessage('error', `File "${file.name}" is not a supported format. Please use PDF or DOCX files.`);
        return false;
    }

    if (file.size > maxSize) {
        showMessage('error', `File "${file.name}" is too large. Maximum size is 10MB.`);
        return false;
    }

    return true;
}

function changePage(newPage) {
    const totalPages = Math.ceil(resumeFiles.length / itemsPerPage);
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        updateResumeFileList();
    }
}

function updateResumeFileList() {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const currentFiles = resumeFiles.slice(startIndex, endIndex);
    const totalPages = Math.ceil(resumeFiles.length / itemsPerPage);

    resumeFileList.innerHTML = '';

    currentFiles.forEach((file, index) => {
        const actualIndex = startIndex + index;
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <i class="fas fa-file-pdf file-icon"></i>
                <div>
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
            </div>
            <button class="remove-file" onclick="removeResumeFile(${actualIndex})">
                <i class="fas fa-times"></i> Remove
            </button>
        `;
        resumeFileList.appendChild(fileItem);
    });

    if (resumeFiles.length > itemsPerPage) {
        const paginationContainer = document.createElement('div');
        paginationContainer.className = 'pagination-container';
        paginationContainer.innerHTML = `
            <div class="pagination-info">
                Showing ${startIndex + 1}-${Math.min(endIndex, resumeFiles.length)} of ${resumeFiles.length} files
            </div>
            <div class="pagination-controls">
                <button class="pagination-btn" onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
                    <i class="fas fa-chevron-left"></i> Previous
                </button>
                <span style="padding: 6px 10px; font-size: 0.8rem; color: #e2e8f0;">
                    Page ${currentPage} of ${totalPages}
                </span>
                <button class="pagination-btn" onclick="changePage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
                    Next <i class="fas fa-chevron-right"></i>
                </button>
            </div>
        `;
        resumeFileList.appendChild(paginationContainer);
    }
}



function updateJDFileList() {
    jdFileList.innerHTML = '';

    if (jdFile) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <i class="fas fa-file-pdf file-icon"></i>
                <div>
                    <div class="file-name">${jdFile.name}</div>
                    <div class="file-size">${formatFileSize(jdFile.size)}</div>
                </div>
            </div>
            <button class="remove-file" onclick="removeJDFile()">
                <i class="fas fa-times"></i> Remove
            </button>
        `;
        jdFileList.appendChild(fileItem);
    }
}

function removeResumeFile(index) {
    resumeFiles.splice(index, 1);

    const totalPages = Math.ceil(resumeFiles.length / itemsPerPage);
    if (currentPage > totalPages && totalPages > 0) {
        currentPage = totalPages;
    } else if (resumeFiles.length === 0) {
        currentPage = 1;
    }

    updateResumeFileList();
    updateProcessButton();
}

function removeJDFile() {
    jdFile = null;
    updateJDFileList();
    updateProcessButton();
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function updateProcessButton() {
    const hasJobDescription = currentMethod === 'text' ?
        jobDescriptionTextarea.value.trim() !== '' :
        jdFile !== null;
    const hasResumeFiles = resumeFiles.length > 0;

    processButton.disabled = !hasJobDescription || !hasResumeFiles;
}

async function processCandidates() {
    setProcessingState(true);
    clearMessages();

    try {
        const formData = new FormData();

        formData.append('threshold', thresholdSlider.value);

        resumeFiles.forEach(file => {
            formData.append('resume_files', file);
        });

        let endpoint;
        if (currentMethod === 'text') {
            formData.append('job_description', jobDescriptionTextarea.value);
            endpoint = '/api/match-candidates';
        } else {
            formData.append('job_description_file', jdFile);
            endpoint = '/api/match-candidates-with-jd-file';
        }

        console.log('Calling endpoint:', endpoint);
        console.log('FormData contents:');
        for (let [key, value] of formData.entries()) {
            console.log(key, value);
        }

        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        console.log('Response status:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Response data:', data);

        if (data.success) {
            showMessage('success', data.message);
            candidatesData = data.candidates;
            displayResults(data);
        } else {
            showMessage('error', data.message || 'Unknown error occurred');
        }

    } catch (error) {
        console.error('Processing error:', error);
        showMessage('error', `Failed to process candidates: ${error.message}`);
    } finally {
        setProcessingState(false);
    }
}

function setProcessingState(isProcessing) {
    processButton.disabled = isProcessing;
    loadingSpinner.style.display = isProcessing ? 'block' : 'none';

    const buttonText = processButton.querySelector('span');
    if (isProcessing) {
        buttonText.textContent = 'Processing...';
    } else {
        buttonText.textContent = 'Process Candidates';
        updateProcessButton();
    }
}

function showMessage(type, message) {
    const messageElement = document.createElement('div');
    messageElement.className = type === 'error' ? 'error-message' : 'success-message';
    messageElement.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-triangle' : 'check-circle'}"></i> ${message}`;

    messageArea.appendChild(messageElement);

    setTimeout(() => {
        messageElement.remove();
    }, 5000);
}

function clearMessages() {
    messageArea.innerHTML = '';
}


function toggleDetails(index) {
    const detailsElement = document.getElementById(`details-${index}`);
    const button = detailsElement.previousElementSibling;
    const icon = button.querySelector('i');
    
    if (detailsElement.style.display === 'none' || detailsElement.style.display === '') {
        detailsElement.style.display = 'block';
        button.innerHTML = '<i class="fas fa-chevron-up"></i> Hide Details';
    } else {
        detailsElement.style.display = 'none';
        button.innerHTML = '<i class="fas fa-chevron-down"></i> Show Details';
    }
}

function displayResults(data) {
    if (!data) {
        showMessage('error', 'No data received from server');
        return;
    }

    document.getElementById('total-candidates').textContent = data.total_candidates || 0;
    document.getElementById('qualified-candidates').textContent = data.candidates_above_threshold || 0;

    const candidates = data.candidates || [];
    const averageScore = candidates.length > 0 ?
        (candidates.reduce((sum, candidate) => sum + (candidate.score || 0), 0) / candidates.length).toFixed(1) : 0;
    document.getElementById('average-score').textContent = averageScore;

    candidatesContainer.innerHTML = '';

    if (candidates.length === 0) {
        candidatesContainer.innerHTML = `
            <div style="text-align: center; padding: 20px; color: #a0aec0;">
                <i class="fas fa-search" style="font-size: 2rem; margin-bottom: 10px;"></i>
                <p>No candidates found above the threshold score of ${thresholdSlider.value}%</p>
            </div>
        `;
    } else {
        candidates.forEach((candidate, index) => {
            if (candidate) {
                const candidateCard = createCandidateCard(candidate, index);
                candidatesContainer.appendChild(candidateCard);
            }
        });
    }

    resultsSection.style.display = 'block';
    document.querySelector('.container').scrollTo({ top: 0, behavior: 'smooth' });
}

function createCandidateCard(candidate, index) {
    if (!candidate) return document.createElement('div');
    
    const card = document.createElement('div');
    card.className = 'candidate-card';
    
    const score = candidate.rating || candidate.score || 0; // Use rating if available, fallback to score
    const scoreColor = score >= 80 ? '#48bb78' : score >= 60 ? '#ed8936' : '#e53e3e';
    
    // Normalize individual_scores keys to lowercase
    const normalizedScores = {};
    if (candidate.individual_scores) {
        Object.keys(candidate.individual_scores).forEach(key => {
            normalizedScores[key.toLowerCase().replace(/\s+/g, '_')] = candidate.individual_scores[key];
        });
    }

    console.log('Candidate data:', { 
        name: candidate.name, 
        score, 
        reason: candidate.reason, 
        individual_scores: normalizedScores 
    }); // Debug log

    // Parse individual scores
    const mandatorySkills = normalizedScores.mandatory_skills 
        ? parseMandatorySkills(normalizedScores.mandatory_skills) 
        : { score: 'N/A', jdSkills: [], matched: [], missing: [], error: 'No data provided' };
    const totalExperience = normalizedScores.total_experience 
        ? parseTotalExperience(normalizedScores.total_experience) 
        : { score: 'N/A', employmentPeriods: [], totalMonths: '', years: '', jdRequirement: '', error: 'No data provided' };
    const relevantExperience = normalizedScores.relevant_experience 
        ? parseRelevantExperience(normalizedScores.relevant_experience) 
        : { score: 'N/A', relevantPeriods: [], totalMonths: '', years: '', jdRequirement: '', threshold: '', error: 'No data provided' };
    const projectExposure = normalizedScores.project_exposure 
        ? parseProjectExposure(normalizedScores.project_exposure) 
        : { score: 'N/A', e2eProjects: [], supportProjects: [], academicUnrelated: [], scoringLogic: '', error: 'No data provided' };

    // Parse scores as numbers for comparison
    const parseScoreValue = (scoreStr) => {
        if (scoreStr === 'N/A' || !scoreStr) return NaN;
        const match = scoreStr.match(/^([\d.]+)\/([\d.]+)/);
        return match ? parseFloat(match[1]) : NaN;
    };

    const mandatorySkillsScore = parseScoreValue(mandatorySkills.score);
    const totalExperienceScore = parseScoreValue(totalExperience.score);
    const relevantExperienceScore = parseScoreValue(relevantExperience.score);
    const projectExposureScore = parseScoreValue(projectExposure.score);

    // Determine if scores should be red
    const isLowMandatorySkills = !isNaN(mandatorySkillsScore) && mandatorySkillsScore < 30;
    const isLowTotalExperience = !isNaN(totalExperienceScore) && totalExperienceScore === 0;
    const isLowRelevantExperience = !isNaN(relevantExperienceScore) && relevantExperienceScore === 0;
    const isLowProjectExposure = !isNaN(projectExposureScore) && projectExposureScore === 0;

    console.log('Score checks:', {
        mandatorySkills: { score: mandatorySkills.score, value: mandatorySkillsScore, isLow: isLowMandatorySkills },
        totalExperience: { score: totalExperience.score, value: totalExperienceScore, isLow: isLowTotalExperience },
        relevantExperience: { score: relevantExperience.score, value: relevantExperienceScore, isLow: isLowRelevantExperience },
        projectExposure: { score: projectExposure.score, value: projectExposureScore, isLow: isLowProjectExposure }
    }); // Debug log for scores

    // Escape HTML to prevent XSS
    const escapeHTML = (str) => {
        if (!str) return str;
        return str.replace(/[&<>"']/g, (match) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[match]));
    };

    card.innerHTML = `
        <div class="candidate-header">
            <div class="candidate-name">${escapeHTML(candidate.name || 'Unknown Candidate')}</div>
            <div class="candidate-score" style="background: ${scoreColor};">
                ${score.toFixed(1)}%
            </div>
        </div>
        <div class="candidate-reason">${escapeHTML(candidate.reason || 'No summary provided')}</div>
        <button class="toggle-details" onclick="toggleDetails(${index})">
            <i class="fas fa-chevron-down"></i> Show Details
        </button>
        <div class="individual-scores" id="details-${index}" style="display: none;">
            <div class="candidate-details">
                ${!normalizedScores || Object.keys(normalizedScores).length === 0 ? `
                    <div class="error-message">No detailed scoring data available for this candidate.</div>
                ` : `
                    <h4 class="${isLowMandatorySkills ? 'low-score' : ''}">Mandatory Skills (Score: ${escapeHTML(mandatorySkills.score)})</h4>
                    ${mandatorySkills.error ? `<div class="error-message">${escapeHTML(mandatorySkills.error)}</div>` : `
                        <h5>JD Skills</h5>
                        <ul>
                            ${mandatorySkills.jdSkills.length ? mandatorySkills.jdSkills.map(skill => `<li>${escapeHTML(skill)}</li>`).join('') : '<li>None</li>'}
                        </ul>
                        <h5>Matched Skills</h5>
                        <ul>
                            ${mandatorySkills.matched.length ? mandatorySkills.matched.map(skill => `<li>${escapeHTML(skill)}</li>`).join('') : '<li>None</li>'}
                        </ul>
                        <h5>Missing Skills</h5>
                        <ul>
                            ${mandatorySkills.missing.length ? mandatorySkills.missing.map(skill => `<li>${escapeHTML(skill)}</li>`).join('') : '<li>None</li>'}
                        </ul>
                    `}
                    
                    <h4 class="${isLowTotalExperience ? 'low-score' : ''}">Total Experience (Score: ${escapeHTML(totalExperience.score)})</h4>
                    ${totalExperience.error ? `<div class="error-message">${escapeHTML(totalExperience.error)}</div>` : `
                        <ul>
                            <li><strong>Employment Periods:</strong> ${totalExperience.employmentPeriods.length ? totalExperience.employmentPeriods.map(p => escapeHTML(p)).join(', ') : 'None'}</li>
                            <li><strong>Total:</strong> ${totalExperience.totalMonths ? `${escapeHTML(totalExperience.totalMonths)} months (${escapeHTML(totalExperience.years)} years)` : 'N/A'}</li>
                            <li><strong>JD Requirement:</strong> ${totalExperience.jdRequirement ? `${escapeHTML(totalExperience.jdRequirement)} years` : 'N/A'}</li>
                        </ul>
                    `}
                    
                    <h4 class="${isLowRelevantExperience ? 'low-score' : ''}">Relevant Experience (Score: ${escapeHTML(relevantExperience.score)})</h4>
                    ${relevantExperience.error ? `<div class="error-message">${escapeHTML(relevantExperience.error)}</div>` : `
                        <ul>
                            <li><strong>Relevant Periods:</strong> ${relevantExperience.relevantPeriods.length ? relevantExperience.relevantPeriods.map(p => escapeHTML(p)).join(', ') : 'None'}</li>
                            <li><strong>Total:</strong> ${relevantExperience.totalMonths ? `${escapeHTML(relevantExperience.totalMonths)} months (${escapeHTML(relevantExperience.years)} years)` : 'N/A'}</li>
                            <li><strong>JD Requirement:</strong> ${relevantExperience.jdRequirement ? `${escapeHTML(relevantExperience.jdRequirement)} years` : 'N/A'}</li>
                            <li><strong>Threshold:</strong> ${relevantExperience.threshold ? `${escapeHTML(relevantExperience.threshold)} year` : 'N/A'}</li>
                        </ul>
                    `}
                    
                    <h4 class="${isLowProjectExposure ? 'low-score' : ''}">Project Exposure (Score: ${escapeHTML(projectExposure.score)})</h4>
                    ${projectExposure.error ? `<div class="error-message">${escapeHTML(projectExposure.error)}</div>` : `
                        <ul>
                            <li><strong>E2E Projects:</strong> ${projectExposure.e2eProjects.length ? projectExposure.e2eProjects.map(p => escapeHTML(p)).join(', ') : 'None'}</li>
                            <li><strong>Support Projects:</strong> ${projectExposure.supportProjects.length ? projectExposure.supportProjects.map(p => escapeHTML(p)).join(', ') : 'None'}</li>
                            <li><strong>Academic/Unrelated:</strong> ${projectExposure.academicUnrelated.length ? projectExposure.academicUnrelated.map(p => escapeHTML(p)).join(', ') : 'None'}</li>
                            <li><strong>Scoring Logic:</strong> ${escapeHTML(projectExposure.scoringLogic) || 'N/A'}</li>
                        </ul>
                    `}
                `}
            </div>
        </div>
    `;
    
    return card;
}


function closeResumeModal() {
    resumeModal.style.display = 'none';
    resumeContent.innerHTML = '';
    resumeModalTitle.textContent = '';
}







document.addEventListener("DOMContentLoaded", function () {
    const downloadButton = document.getElementById("download-csv-btn");

    if (downloadButton) {
        downloadButton.addEventListener("click", async function () {
            try {
                const response = await fetch("/api/download-shortlisted");

                if (!response.ok) {
                    alert("❌ CSV not found or something went wrong!");
                    return;
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "shortlisted_candidates.csv";
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            } catch (err) {
                console.error("CSV download error:", err);
                alert("⚠️ Failed to download the CSV. Try again later.");
            }
        });
    }
});





class HeaderMenuManager {
    constructor() {
        this.menuToggle = document.getElementById("menu-toggle");
        this.navMenu = document.getElementById("nav-menu");
        this.profileButton = document.getElementById("profile-menu-button");
        this.profileMenu = document.getElementById("profile-menu");
        this.logoutBtn = document.getElementById("logout-btn");
        
        this.init();
    }

    // Initialize all menu functionality
    init() {
        this.setupMenuToggle();
        this.setupProfileDropdown();
        this.setupLogoutHandler();
        this.setupWindowResize();
        this.setupKeyboardNavigation();
    }

    // Toggle mobile menu
    setupMenuToggle() {
        if (this.menuToggle && this.navMenu) {
            this.menuToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                this.navMenu.classList.toggle('show');
                
                // Close profile menu if open
                if (this.profileMenu && this.profileMenu.classList.contains('show')) {
                    this.profileMenu.classList.remove('show');
                }
            });
        }
    }

    // Toggle profile dropdown
    setupProfileDropdown() {
        if (this.profileButton && this.profileMenu) {
            this.profileButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.profileMenu.classList.toggle('show');
                
                // Close mobile menu if open
                if (this.navMenu && this.navMenu.classList.contains('show')) {
                    this.navMenu.classList.remove('show');
                }
            });

            // Close dropdown if clicked outside
            document.addEventListener('click', (e) => {
                if (
                    !this.profileButton.contains(e.target) &&
                    !this.profileMenu.contains(e.target)
                ) {
                    this.profileMenu.classList.remove('show');
                }
                
                // Also close mobile menu if clicked outside
                if (
                    this.navMenu &&
                    !this.menuToggle.contains(e.target) &&
                    !this.navMenu.contains(e.target)
                ) {
                    this.navMenu.classList.remove('show');
                }
            });
        }
    }

    // Setup logout functionality
    setupLogoutHandler() {
        if (this.logoutBtn) {
            this.logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Show confirmation dialog
                if (confirm('Are you sure you want to sign out?')) {
                    // Clear any stored data
                    localStorage.clear();
                    sessionStorage.clear();
                    
                    // Redirect to login page or home
                    window.location.href = '/'; // Change this to your login page URL
                }
            });
        }
    }

    // Handle window resize to close mobile menu
    setupWindowResize() {
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                // Close mobile menu on desktop
                if (this.navMenu && this.navMenu.classList.contains('show')) {
                    this.navMenu.classList.remove('show');
                }
            }
        });
    }

    // Setup keyboard navigation
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Close dropdowns on Escape key
            if (e.key === 'Escape') {
                if (this.profileMenu && this.profileMenu.classList.contains('show')) {
                    this.profileMenu.classList.remove('show');
                    this.profileButton.focus();
                }
                if (this.navMenu && this.navMenu.classList.contains('show')) {
                    this.navMenu.classList.remove('show');
                    this.menuToggle.focus();
                }
            }
        });
    }
}

// Initialize the header menu when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize header menu (only if elements exist)
    const profileButton = document.getElementById('profile-menu-button');
    if (profileButton) {
        new HeaderMenuManager();
    }
});