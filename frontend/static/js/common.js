// static/js/common.js
// GENERIC REUSABLE FUNCTIONS FOR ALL REVIEWS - UPDATED TO SUPPORT TEXT AND NUMERIC INPUTS

let isLoading = false;

// Get current review number from page context
function getCurrentReviewNumber() {
    const path = window.location.pathname;
    if (path.includes('review1')) return 1;
    if (path.includes('review2')) return 2;
    if (path.includes('review3')) return 3;
    if (path.includes('review4')) return 4;
    if (path.includes('review6')) return 6;
    if (path.includes('review5')) return 5;
    if (path.includes('review0')) return 0;
    return 1; // default
}

// ==================== ATTENDANCE FUNCTIONS ====================

async function fetchMembers() {
    const groupId = document.getElementById("group_id").value.trim();
    if (!groupId) {
        alert("Please enter a Group ID first!");
        return;
    }

    const reviewNumber = getCurrentReviewNumber();
    console.log(`Fetching members for Review ${reviewNumber}`);

    try {
        const response = await fetch(`/api/members?group_id=${groupId}&review_number=${reviewNumber}`);
        const data = await response.json();
        
        console.log("Fetched members data:", data);

        const tbody = document.getElementById("attendance-tbody");
        tbody.innerHTML = "";

        if (data.error) {
            alert(data.error);
            return;
        }

        if (data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3">No members found for this Group ID</td></tr>`;
            return;
        }

        data.forEach(member => {
            const row = document.createElement("tr");
            const isPresent = member.attendance === 1 || member.attendance === true;
            
            row.innerHTML = `
                <td class="roll-no">${member.roll_no}</td>
                <td class="student-name">${member.name}</td>
                <td class="present-cell">
                    <input type="checkbox" 
                           class="attendance-checkbox" 
                           name="present_${member.roll_no}"
                           data-roll="${member.roll_no}"
                           ${isPresent ? 'checked' : ''}>
                </td>
            `;
            tbody.appendChild(row);
            
            console.log(`Member ${member.roll_no}: attendance=${member.attendance}, checked=${isPresent}`);
        });

        attachCheckboxListeners();

    } catch (error) {
        console.error("Error fetching members:", error);
        alert("Failed to load members");
    }
}

async function saveIndividualAttendance(rollNo, isPresent) {
    const groupId = document.getElementById("group_id").value.trim();
    if (!groupId) {
        alert("Please enter Group ID first!");
        return;
    }

    const reviewNumber = getCurrentReviewNumber();
    console.log(`Saving attendance for Review ${reviewNumber}:`, { group_id: groupId, roll_no: rollNo, present: isPresent });

    try {
        const response = await fetch(`/api/review${reviewNumber}/attendance`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                group_id: groupId,
                attendance: [{
                    roll_no: rollNo,
                    present: isPresent
                }]
            })
        });

        const data = await response.json().catch(() => null);
        console.log("Attendance save response:", response.status, data);

        if (!response.ok) {
            console.error("Failed to save attendance");
            alert("Failed to save attendance");
        }
    } catch (err) {
        console.error("Network error:", err);
        alert("Network error while saving attendance");
    }
}

function attachCheckboxListeners() {
    document.querySelectorAll(".attendance-checkbox").forEach(cb => {
        cb.addEventListener("change", async (e) => {
            const rollNo = e.target.dataset.roll;
            const isPresent = e.target.checked;

            await saveIndividualAttendance(rollNo, isPresent);
            updateMarksForAttendance(rollNo, isPresent);
            
            if (typeof applyAbsentStudents === 'function') {
                applyAbsentStudents();
            }
            if (typeof setupKeyboardNavigation === 'function') {
                setupKeyboardNavigation();
            }
        });
    });
}

function updateMarksForAttendance(rollNo, isPresent) {
    document.querySelectorAll(".mark-input").forEach(inp => {
        const name = inp.name;
        const inputRoll = name.substring(name.lastIndexOf("_") + 1);

        if (inputRoll === rollNo) {
            const inputType = inp.dataset.inputType || 'number';
            
            if (!isPresent) {
                // Absent: Set appropriate default value
                if (inputType === 'text') {
                    inp.value = "N"; // N = Not present/applicable
                } else {
                    inp.value = "0";
                }
                inp.style.backgroundColor = "#eee";
                inp.dataset.absent = "true";
                inp.readOnly = true;
                inp.title = "Double-click to edit marks for absent student";
            } else {
                // Present: Clear value
                inp.value = "";
                inp.style.backgroundColor = "";
                inp.dataset.absent = "false";
                inp.readOnly = true;
                inp.title = "Click to edit";
            }
        }
    });

    if (typeof calculateTotals === 'function') {
        calculateTotals();
    }
}

// ==================== GENERIC DATA LOADING ====================

async function loadAllGroupData(config) {
    if (isLoading) {
        console.log("Already loading data, skipping...");
        return;
    }

    const groupId = document.getElementById("group_id").value.trim();
    
    if (!groupId) {
        console.log("No group ID entered");
        return;
    }

    isLoading = true;
    console.log(`=== Loading all data for Review ${config.reviewNumber}, group: ${groupId} ===`);

    try {
        // 1. Load attendance table
        console.log("Step 1: Loading attendance...");
        await fetchMembers();
        
        // 2. Load evaluation/marks table
        console.log("Step 2: Loading marks table...");
        await loadEvaluationTable(config);
        
        // 3. Load existing questionnaire responses
        console.log("Step 3: Loading questionnaire responses...");
        await loadExistingResponses(config.reviewNumber);
        
        // 4. Apply absent student styling
        console.log("Step 4: Applying absent student styling...");
        applyAbsentStudents();
        
        // 5. Setup keyboard navigation
        console.log("Step 5: Setting up keyboard navigation...");
        setupKeyboardNavigation();
        
        console.log("=== All data loaded successfully ===");
    } catch (error) {
        console.error("Error loading group data:", error);
    } finally {
        isLoading = false;
    }
}

// ==================== GENERIC EVALUATION TABLE (UPDATED FOR TEXT & NUMERIC) ====================

async function loadEvaluationTable(config) {
    const groupId = document.getElementById("group_id").value.trim();
    if (!groupId) return;

    const res = await fetch(`/api/members?group_id=${groupId}&review_number=${config.reviewNumber}`);
    const members = await res.json();

    const thead = document.getElementById("performance-thead");
    const tbody = document.getElementById("performance-tbody");
    const tfoot = document.getElementById("performance-tfoot");

    if (!members || members.length === 0) {
        thead.innerHTML = "";
        tbody.innerHTML = "<tr><td colspan='10'>No members found</td></tr>";
        tfoot.innerHTML = "";
        return;
    }

    thead.innerHTML = `
        <tr>
            <th>Particulars</th>
            ${members.map(m => `<th>${m.name}</th>`).join("")}
        </tr>
    `;

    tbody.innerHTML = config.criteria.map(c => {
        const inputType = c.type || 'number'; // Default to number if not specified
        const isTextInput = inputType === 'text';
        
        return `
            <tr>
                <td>${c.label}</td>
                ${members.map(m => {
                    if (isTextInput) {
                        // Text input (Y/N fields)
                        return `
                            <td>
                                <input type="text"
                                       name="${c.name}_${m.roll_no}"
                                       class="mark-input text-input"
                                       data-input-type="text"
                                       placeholder="Y/N"
                                       maxlength="1"
                                       style="text-transform: uppercase;"
                                       oninput="handleTextInput(this)">
                            </td>
                        `;
                    } else {
                        // Numeric input (marks)
                        return `
                            <td>
                                <input type="number"
                                       min="0" max="${c.max}" step="0.5"
                                       name="${c.name}_${m.roll_no}"
                                       class="mark-input numeric-input"
                                       data-input-type="number"
                                       oninput="handleMarkInput(this, ${c.max})">
                            </td>
                        `;
                    }
                }).join("")}
            </tr>
        `;
    }).join("");

    tfoot.innerHTML = `
        <tr>
            <th>Total (${config.totalMarks}M)</th>
            ${members.map(m => `<th><input type="text" readonly id="total_${m.roll_no}" value="0.0"></th>`).join("")}
        </tr>
    `;

    addHintMessage();
    await loadExistingMarks(config.reviewNumber, groupId);
    calculateTotals();
}

function addHintMessage() {
    const tableContainer = document.querySelector("#performance-tbody")?.closest('table')?.parentElement;
    if (!tableContainer) return;
    
    const existingHint = document.getElementById("marks-hint");
    if (existingHint) existingHint.remove();

    const hint = document.createElement("div");
    hint.id = "marks-hint";
    hint.style.cssText = "margin-top: 10px; padding: 10px; background-color: #e8f4fd; border-left: 4px solid #2196F3; color: #333; font-size: 14px;";
    hint.innerHTML = `
        <strong>Tip:</strong> 
        <span style="color: #555;">Click to edit marks for present students.</span> 
        <span style="color: #d32f2f; font-weight: 500;">Double-click to edit marks for absent students.</span>
        <span style="color: #666;"> (Y/N fields for text responses, numeric fields for marks)</span>
    `;
    
    tableContainer.appendChild(hint);
}

async function loadExistingMarks(reviewNumber, groupId) {
    try {
        const response = await fetch(`/api/review${reviewNumber}/marks?group_id=${groupId}`);
        if (!response.ok) {
            console.log("No existing marks found");
            return;
        }

        const data = await response.json();
        console.log(`Review ${reviewNumber} marks data received:`, data);
        
        if (data && data.length > 0) {
            let marksCount = 0;
            data.forEach(studentMarks => {
                const rollNo = studentMarks.roll_no;
                
                // Get all keys except system columns
                const criteriaKeys = Object.keys(studentMarks).filter(key => 
                    !['id', 'group_id', 'roll_no', 'total', 'created_at', 'updated_at'].includes(key)
                );

                criteriaKeys.forEach(criterion => {
                    const input = document.querySelector(`input[name="${criterion}_${rollNo}"]`);
                    if (input && studentMarks[criterion] !== null && studentMarks[criterion] !== undefined) {
                        input.value = studentMarks[criterion];
                        marksCount++;
                    }
                });
            });

            console.log(`Loaded marks for ${data.length} students (${marksCount} total marks)`);
            calculateTotals();
        }
    } catch (err) {
        console.error("Error loading marks:", err);
    }
}

// ==================== GENERIC RESPONSES LOADING ====================

async function loadExistingResponses(reviewNumber) {
    const groupId = document.getElementById("group_id").value.trim();
    if (!groupId) return;

    try {
        console.log(`Fetching Review ${reviewNumber} responses for group: ${groupId}`);
        const response = await fetch(`/api/review${reviewNumber}/responses?group_id=${groupId}`);
        
        console.log(`Response status: ${response.status}`);
        
        if (response.status === 404) {
            console.log("No existing responses found - this is a new submission");
            clearResponseForm();
            return;
        }

        if (!response.ok) {
            throw new Error(`Failed to load responses: ${response.status}`);
        }

        const data = await response.json();
        console.log(`Received Review ${reviewNumber} response data:`, data);

        // Fill in date
        if (data.submission_date) {
            const dateField = document.getElementById("date");
            if (dateField) {
                dateField.value = data.submission_date;
                console.log(`Date set to: ${data.submission_date}`);
            }
        }

        // Fill in comments
        if (data.comments) {
            const commentsField = document.getElementById("comments");
            if (commentsField) {
                commentsField.value = data.comments;
                console.log("Comments loaded");
            }
        }

        // Check radio buttons and fill numeric inputs
        if (data.responses) {
            console.log("Loading radio responses:", data.responses);
            let responseCount = 0;
            Object.entries(data.responses).forEach(([questionCode, value]) => {
                // Try to find radio button first
                const radio = document.querySelector(`input[name="${questionCode}"][value="${value}"]`);
                if (radio) {
                    radio.checked = true;
                    responseCount++;
                } else {
                    // Try to find numeric input
                    const numInput = document.querySelector(`input[type="number"][name="${questionCode}"]`);
                    if (numInput) {
                        numInput.value = value;
                        responseCount++;
                    } else {
                        console.warn(`Input not found: name="${questionCode}", value="${value}"`);
                    }
                }
            });
            console.log(`Loaded ${responseCount} question responses`);
        }

        showUpdateIndicator(data.updated_at || data.created_at);

    } catch (err) {
        console.error("Error loading responses:", err);
    }
}

function clearResponseForm() {
    document.querySelectorAll('input[type="radio"]').forEach(radio => radio.checked = false);
    
    const commentsField = document.getElementById("comments");
    if (commentsField) commentsField.value = "";
    
    const dateField = document.getElementById("date");
    if (dateField) dateField.value = "";
    
    const indicator = document.getElementById("update-indicator");
    if (indicator) indicator.remove();
    
    console.log("Form cleared for new submission");
}

function showUpdateIndicator(lastUpdated) {
    const existing = document.getElementById("update-indicator");
    if (existing) existing.remove();
    
    const saveSection = document.querySelector(".save-section") || document.querySelector(".button-group");
    if (!saveSection) return;
    
    const indicator = document.createElement("div");
    indicator.id = "update-indicator";
    indicator.style.cssText = `
        margin-top: 10px;
        padding: 8px 12px;
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        color: #856404;
        font-size: 14px;
        border-radius: 4px;
    `;
    
    const dateStr = lastUpdated ? new Date(lastUpdated).toLocaleString() : 'Unknown';
    indicator.innerHTML = `
        <strong>Editing Mode:</strong> 
        This submission already exists (last updated: ${dateStr}). 
        Saving will <strong>update</strong> the existing data.
    `;
    
    saveSection.parentElement.insertBefore(indicator, saveSection);
}

// ==================== INPUT VALIDATION (UPDATED FOR TEXT & NUMERIC) ====================

function handleTextInput(input) {
    // Convert to uppercase and limit to Y, N, or single character
    let value = input.value.toUpperCase().trim();
    
    // Allow Y, N, or leave empty
    if (value && !['Y', 'N'].includes(value)) {
        // Allow any single character but warn if not Y/N
        value = value.charAt(0);
    }
    
    input.value = value;
}

function handleMarkInput(input, max) {
    validateMark(input, max);
    calculateTotals();
}

function validateMark(input, max) {
    let v = parseFloat(input.value);
    if (isNaN(v)) {
        input.value = "";
        return;
    }

    if (v > max) v = max;
    if (v < 0) v = 0;

    v = Math.round(v * 2) / 2;
    input.value = (v % 1 === 0) ? String(v) : v.toFixed(1);
}

function calculateTotals() {
    const totals = {};

    document.querySelectorAll(".mark-input").forEach(inp => {
        const name = inp.getAttribute("name") || "";
        const lastUnderscore = name.lastIndexOf("_");
        if (lastUnderscore === -1) return;

        const roll = name.slice(lastUnderscore + 1);
        const inputType = inp.dataset.inputType || 'number';
        
        // Only count numeric inputs in total
        if (inputType === 'number') {
            const val = parseFloat(inp.value);
            if (!isNaN(val)) {
                totals[roll] = (totals[roll] || 0) + val;
            }
        }
    });

    document.querySelectorAll('[id^="total_"]').forEach(tf => {
        const roll = tf.id.replace("total_", "");
        const t = totals[roll] || 0;
        tf.value = t.toFixed(1);
    });
}

// ==================== KEYBOARD NAVIGATION (UPDATED) ====================

function setupKeyboardNavigation() {
    const inputs = Array.from(document.querySelectorAll(".mark-input"));

    inputs.forEach(inp => {
        inp.readOnly = true;

        inp.addEventListener("click", () => {
            if (inp.dataset.absent !== "true") {
                inp.readOnly = false;
                inp.focus();
            }
        });

        inp.addEventListener("dblclick", () => {
            if (inp.dataset.absent === "true") {
                inp.readOnly = false;
                inp.focus();
                inp.style.backgroundColor = "#fffacd";
                inp.title = "Editing absent student's marks (Double-clicked to override)";
            }
        });

        inp.addEventListener("blur", () => {
            inp.readOnly = true;
            if (inp.dataset.absent === "true") {
                inp.style.backgroundColor = "#eee";
                inp.title = "Double-click to edit marks for absent student";
            }
        });

        inp.addEventListener("keydown", (e) => {
            if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Tab"].includes(e.key)) {
                e.preventDefault();
                navigateToNextCell(inp, e.key, inputs);
            }
        });
    });
}

function navigateToNextCell(currentInput, key, allInputs) {
    const totalCols = document.querySelectorAll("#performance-thead th").length - 1;

    const index = allInputs.indexOf(currentInput);
    if (index === -1) return;

    let nextIndex = index;

    switch (key) {
        case "ArrowRight":
        case "Tab":
            nextIndex = index + 1;
            break;
        case "ArrowLeft":
            nextIndex = index - 1;
            break;
        case "ArrowUp":
            nextIndex = index - totalCols;
            break;
        case "ArrowDown":
            nextIndex = index + totalCols;
            break;
    }

    if (nextIndex < 0 || nextIndex >= allInputs.length) return;

    let nextInput = allInputs[nextIndex];

    while (nextInput && isAbsentStudent(nextInput)) {
        if (key === "ArrowRight" || key === "Tab") nextIndex++;
        else if (key === "ArrowLeft") nextIndex--;
        else if (key === "ArrowUp") nextIndex -= totalCols;
        else if (key === "ArrowDown") nextIndex += totalCols;

        if (nextIndex < 0 || nextIndex >= allInputs.length) return;
        nextInput = allInputs[nextIndex];
    }

    if (nextInput) {
        nextInput.focus();
        nextInput.readOnly = false;
    }
}

function applyAbsentStudents() {
    const rows = document.querySelectorAll("#attendance-tbody tr");
    const absentRolls = [];

    rows.forEach(row => {
        const rollCell = row.querySelector(".roll-no");
        const checkbox = row.querySelector(".attendance-checkbox");
        
        if (rollCell && checkbox && !checkbox.checked) {
            absentRolls.push(rollCell.textContent.trim());
        }
    });

    document.querySelectorAll(".mark-input").forEach(inp => {
        const name = inp.name;
        const roll = name.substring(name.lastIndexOf("_") + 1);

        if (absentRolls.includes(roll)) {
            const inputType = inp.dataset.inputType || 'number';
            
            if (inputType === 'text') {
                inp.value = "N";
            } else {
                inp.value = "0";
            }
            
            inp.style.backgroundColor = "#eee";
            inp.dataset.absent = "true";
            inp.readOnly = true;
            inp.title = "Double-click to edit marks for absent student";
        } else {
            inp.style.backgroundColor = "";
            inp.dataset.absent = "false";
            inp.readOnly = true;
            inp.title = "Click to edit";
        }
    });

    calculateTotals();
}

function isAbsentStudent(input) {
    return input.dataset.absent === "true";
}

// ==================== GENERIC SAVE FUNCTIONS ====================

async function saveMarks(reviewNumber, criteriaNames) {
    const groupId = document.getElementById("group_id").value.trim();
    if (!groupId) return false;

    const marksData = [];
    const rollNumbers = new Set();
    
    document.querySelectorAll(".mark-input").forEach(inp => {
        const name = inp.name;
        const roll = name.substring(name.lastIndexOf("_") + 1);
        rollNumbers.add(roll);
    });

    rollNumbers.forEach(roll => {
        const studentMarks = {
            group_id: groupId,
            roll_no: roll
        };

        criteriaNames.forEach(criterion => {
            const input = document.querySelector(`input[name="${criterion}_${roll}"]`);
            if (input) {
                const inputType = input.dataset.inputType || 'number';
                
                if (inputType === 'text') {
                    // Store text value (Y/N)
                    studentMarks[criterion] = input.value.trim().toUpperCase() || null;
                } else {
                    // Store numeric value
                    studentMarks[criterion] = parseFloat(input.value) || 0;
                }
            }
        });

        marksData.push(studentMarks);
    });

    try {
        const response = await fetch(`/api/review${reviewNumber}/marks`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ marks: marksData })
        });

        const data = await response.json().catch(() => null);

        if (response.ok) {
            return true;
        } else {
            console.error(`Failed to save marks: ${data?.error || 'Unknown error'}`);
            return false;
        }
    } catch (err) {
        console.error("Network error in saveMarks:", err);
        return false;
    }
}

async function saveForm(reviewNumber, criteriaNames) {
    const groupId = document.getElementById("group_id").value.trim();
    const date = document.getElementById("date").value;
    const comments = document.getElementById("comments").value.trim();

    if (!groupId) {
        alert("Please enter Group ID!");
        return;
    }

    if (!date) {
        alert("Please select a date!");
        return;
    }

    const responses = [];
    
    // Collect radio button responses
    document.querySelectorAll('input[type="radio"]:checked').forEach(radio => {
        responses.push({
            question_code: radio.name,
            response_value: radio.value
        });
    });
    
    // Collect numeric question responses (e.g., que_4.1.6)
    document.querySelectorAll('input[type="number"][name^="que_"]').forEach(numInput => {
        if (numInput.value && numInput.value.trim() !== '') {
            responses.push({
                question_code: numInput.name,
                response_value: parseFloat(numInput.value)
            });
        }
    });

    try {
        const responsePayload = {
            group_id: groupId,
            date: date,
            comments: comments,
            responses: responses
        };

        const responseRes = await fetch(`/api/review${reviewNumber}/responses`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(responsePayload)
        });

        const responseData = await responseRes.json().catch(() => null);

        if (!responseRes.ok) {
            throw new Error(responseData?.error || "Failed to save questionnaire responses");
        }

        const marksSuccess = await saveMarks(reviewNumber, criteriaNames);
        
        if (marksSuccess) {
            const action = responseData?.action === 'updated' ? 'updated' : 'saved';
            alert(`Form ${action} successfully!\n\nGroup: ${groupId}\nDate: ${date}\nResponses: ${responses.length} questions\nAction: ${responseData?.action || 'saved'}`);
        } else {
            alert("Responses saved, but marks save failed. Please try saving again.");
        }

    } catch (err) {
        console.error("Error saving form:", err);
        alert("Error saving form: " + err.message);
    }
}

async function generatePDF(reviewNumber) {
    const groupId = document.getElementById("group_id").value.trim();
    
    if (!groupId) {
        alert("Please enter Group ID!");
        return;
    }
    
    const btn = document.getElementById("generate-pdf");
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Generating PDF...";
    
    try {
        const response = await fetch(`/api/review${reviewNumber}/generate-pdf`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ group_id: groupId })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            alert(`PDF generated successfully!`);
            window.open(data.download_url, '_blank');
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (err) {
        console.error("Error generating PDF:", err);
        alert("Failed to generate PDF");
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function previousReview(prevUrl) {
    window.location.href = prevUrl;
}

function nextReview(nextUrl) {
    window.location.href = nextUrl;
}


// ==================== GENERIC INITIALIZATION ====================

function initializeReviewPage(config) {
    console.log(`Review ${config.reviewNumber} - DOM Content Loaded`);
    
    const groupField = document.getElementById("group_id");
    if (groupField) {
        const newGroupField = groupField.cloneNode(true);
        groupField.parentNode.replaceChild(newGroupField, groupField);
        
        newGroupField.addEventListener("change", () => loadAllGroupData(config));
        newGroupField.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                loadAllGroupData(config);
            }
        });
        console.log("Group field listeners attached");
    }

    // Set up PDF button
    const pdfBtn = document.getElementById("generate-pdf");
    if (pdfBtn) {
        pdfBtn.onclick = () => generatePDF(config.reviewNumber);
    }

    // Set up navigation buttons
    const backBtn = document.getElementById("back-review");
    if (backBtn && config.previousReview) {
        backBtn.onclick = () => previousReview(config.previousReview);
    }

    const nextBtn = document.getElementById("next-review");
    if (nextBtn && config.nextReview) {
        nextBtn.onclick = () => nextReview(config.nextReview);
    }

        // Set up save button
    const saveBtn = document.getElementById("save-form");
    if (saveBtn || pdfBtn || newBtn) {
        saveBtn.onclick = () => saveForm(config.reviewNumber, config.criteria.map(c => c.name));
    }

    console.log(`Review ${config.reviewNumber} initialization complete`);
}

// Menu toggle function (used in header)
function toggleMenu() {
    const menu = document.getElementById('menuDropdown');
    if (menu) {
        menu.classList.toggle('show');
    }
}

// Close menu when clicking outside
document.addEventListener('click', function(event) {
    const menu = document.getElementById('menuDropdown');
    const toggle = document.querySelector('.menu-toggle');
    
    if (menu && toggle && !menu.contains(event.target) && !toggle.contains(event.target)) {
        menu.classList.remove('show');
    }
});


// ==================== ROLE-BASED UI ADJUSTMENTS ====================

function setupRoleBasedUI() {
    // Check if user role is available (from server-rendered template)
    const userRole = document.body.dataset.userRole || 'user';
    const isAdmin = userRole === 'admin';
    
    if (!isAdmin) {
        // Hide admin-only menu items for non-admin users
        const adminMenuItems = document.querySelectorAll('.menu-item[data-admin-only="true"]');
        adminMenuItems.forEach(item => {
            item.style.display = 'none';
        });
        
        // Redirect if somehow accessed admin pages
        const adminPages = ['/data-manager', '/scheduler', '/attendance-dashboard', '/pdf-viewer'];
        const currentPath = window.location.pathname;
        
        if (adminPages.some(page => currentPath.startsWith(page))) {
            alert('Access denied. Admin privileges required.');
            window.location.href = '/';
        }
    }
}

// Call on page load
document.addEventListener('DOMContentLoaded', setupRoleBasedUI);


// ==================== THEME TOGGLE FUNCTIONALITY ====================

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
});

/**
 * Initialize theme based on localStorage or system preference
 */
function initializeTheme() {
    // Check if user has a saved theme preference
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme) {
        // Use saved theme
        setTheme(savedTheme);
    } else {
        // Check system preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        setTheme(prefersDark ? 'dark' : 'light');
    }
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        // Only auto-switch if user hasn't manually set a preference
        if (!localStorage.getItem('theme')) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });
}

/**
 * Toggle between light and dark theme
 */
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    // Add transition class for smooth theme change
    document.body.classList.add('theme-transitioning');
    
    // Add rotation animation to toggle button
    const toggleBtn = document.querySelector('.theme-toggle');
    if (toggleBtn) {
        toggleBtn.classList.add('rotating');
        setTimeout(() => {
            toggleBtn.classList.remove('rotating');
        }, 500);
    }
    
    // Set new theme
    setTheme(newTheme);
    
    // Remove transition class after animation completes
    setTimeout(() => {
        document.body.classList.remove('theme-transitioning');
    }, 300);
}

/**
 * Set theme and save preference
 * @param {string} theme - 'light' or 'dark'
 */
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    // Update toggle button appearance if it exists
    updateToggleButton(theme);
    
    console.log(`Theme set to: ${theme}`);
}

/**
 * Update toggle button icon based on current theme
 * @param {string} theme - current theme
 */
function updateToggleButton(theme) {
    const toggleBtn = document.querySelector('.theme-toggle');
    if (!toggleBtn) return;
    
    // Optional: Add aria-label for accessibility
    toggleBtn.setAttribute('aria-label', 
        theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'
    );
}

/**
 * Get current theme
 * @returns {string} - current theme ('light' or 'dark')
 */
function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'light';
}

/**
 * Reset theme to system preference
 */
function resetTheme() {
    localStorage.removeItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setTheme(prefersDark ? 'dark' : 'light');
}

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeTheme,
        toggleTheme,
        setTheme,
        getCurrentTheme,
        resetTheme
    };
}