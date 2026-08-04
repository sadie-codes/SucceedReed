/**
 * @fileoverview This file is used in conjunction with home.html to give it its functionality.
 * Example actions: opening popups, displaying errors, clicking buttons, and using fetch to send
 * or receive information from app.py. 
 */
const reedPopup = document.getElementById("reed-popup");
const sessionPopup = document.getElementById('session-popup');
const helpPopup = document.getElementById('help-popup');

const menu = document.getElementById("options-menu");
const menu_delete = document.getElementById("options-menu-delete");
const menu_view = document.getElementById("options-menu-view");
let activeListener = null;
let closedEventListener = true;
let btn_clicked = null;

const deletePopup = document.getElementById("delete-popup");
const deleteHeader = document.getElementById("delete-header");

const viewPopup = document.getElementById("view-popup");
const viewPopupInfo = document.getElementById("view-info-popup");
const viewPopupText = document.getElementById("view-popup-text");

const best_reed_element = document.getElementById("best-reed");
const best_breakin_element = document.getElementById("rec-break-in");

const break_in_box = document.getElementById("break-in-box");
const rec_box = document.getElementById("rec-box");

const rec_table = document.getElementById('rec-table');
const break_in_table = document.getElementById('break-in-table');

const errorBlank = document.getElementById("input-blank");
const errorExists = document.getElementById("input-existing");
const errorType = document.getElementById("input-incorrect-type");
const errors = [errorBlank, errorExists, errorType];

const ratingSelected = undefined;
const happyBtn = document.getElementById("happy-face-btn");
const okBtn = document.getElementById("ok-face-btn");
const sadBtn = document.getElementById("sad-face-btn");
const btns = [happyBtn, okBtn, sadBtn];

const notSelected = document.getElementById("face-not-selected");
const blank = document.getElementById("blank");
const idNotValid = document.getElementById("id-not-valid");
const notInt = document.getElementById("minutes-not-integer");
const sessionErrors = [notSelected, blank, idNotValid, notInt];

async function getReedData() {
    try {
        const response = await fetch('/get-all-data');
        const reedData = await response.json();
        return reedData;
    } catch(error) {
        console.log('Error from API ', error);
    }
}

async function refreshTables() {
    await fetch('/get-rec-data') //request the data from the webpage via flask for rendering table
        .then(response => response.json())
        .then(data => {
            render_rec_table(data);
            })
        .catch(error => console.error('Error fetching data: ', error));

    await fetch('/get-breakin-data') //request the data from the webpage via flask for rendering table
        .then(response => response.json())
        .then(data => {
            render_breakin_table(data);
            load_best_reeds();
            })
        .catch(error => console.error('Error fetching data: ', error));
}

window.onload = function() {
    //on reload, the site gets data for both tables and loads them to constantly update info
    refreshTables();
}


function addRowFromInput(){
    /**
     * Adds a row to the break_in_table after the user adds a reed.
     * Uses fetch to save the reed data and updates the table.
     */
    let row = break_in_table.insertRow(-1);
    row.classList.add("reed-rows");
    let id = row.insertCell(0);
    let type = row.insertCell(1);
    let step = row.insertCell(2);

    reed_id = String(document.getElementById('reed-id').value);
    reed_type = String(document.getElementById('reed-type').value);
    reed_strength = String(document.getElementById('reed-strength').value);

    id.innerHTML = reed_id
    type.innerHTML = reed_type
    //the default of the step is 1, so there is no need to retrieve it
    step.innerHTML = String(1);
    //an object is used to send the data over to python using json
    const obj_format = {"reed_id": reed_id,
                   "reed_type": reed_type,
                   "reed_strength": reed_strength
    };

    //sets each input field to an empty string to reset the form, so the previous input doesn't appear again
    document.getElementById('reed-id').value = "";
    document.getElementById('reed-strength').value = "";
    document.getElementById('reed-type').value = "";

    fetch('/save-reed-data',
        {"method": "POST",
         "headers": {
            "Content-Type": "application/json"
         },
         "body": JSON.stringify(obj_format)
        }
    ) 
        .then(response => {
            if (!response.ok) {
                console.error('Server responded with an error status:', response.status);
            } else {
                console.log('Reed saved successfully!');
            }
        });
}

function render_breakin_table(data) {
    /**
     * Renders the break-in table with the existing data from the database.
     * Uses fetch to retrieve it.
     * @param {Object} data
     */
    break_in_table.innerHTML = ''; //clear existing items

    //an extra header is added to create space for the options button
    const headers = ["ID", "Type", "Step", "Rest", "Optimal Playtime", "  "];
    const headerRow = break_in_table.insertRow(-1);
    headers.forEach(text => {
        const th = document.createElement("th");
        th.classList.add("rec-titles");
        th.textContent = text;
        headerRow.appendChild(th);
    }
    );
    
    data.reeds.forEach(reed => {
        let row = break_in_table.insertRow(-1);
        row.classList.add("reed-rows");
        let id = row.insertCell(0);
        let type = row.insertCell(1);
        let step = row.insertCell(2);
        let days_last_played = row.insertCell(3);
        let playtime = row.insertCell(4);
        let options = row.insertCell(5);
        //creates an options button for each reed using direct html, since we don't know directly the number of reeds
        //the is is reed.id + "-options" to make it easily accessible for accessing
        options.innerHTML = `<button id=${reed.id + "-options"} class='options-btn'><img id=${reed.id + "-options-img"} class='options-img' src='/static/marks/options.png'></button>`;
        document.getElementById(reed.id + "-options").addEventListener("click", () => {openMenuPopup(reed.id + "-options")});
        
        id.innerHTML = reed.id;
        type.innerHTML = reed.reed_type;
        step.innerHTML = reed.step + "/5";
        //checks if days_last_played is equal to none to use either day or days as the unit label
        days_last_played.innerHTML = reed.days_last_played == 1 ? `${reed.days_last_played} day`: `${reed.days_last_played} days`;
        playtime.innerHTML = reed.recommended_time + " min";
    })
}
function render_rec_table(data){
    /**
     * Renders the recommended reed table using the data from the database.
     * Uses fetch to get the data and update the table upon load.
     * @param {Object} data
     */
    rec_table.innerHTML = ''; //clear existing items

    //an extra header is added to create space for the options button
    const headers = ["ID", "Type", "Health", "Rested", " "];
    const headerRow = rec_table.insertRow(-1);
    headers.forEach(text => {
        const th = document.createElement("th");
        th.classList.add("rec-titles");
        th.textContent = text;
        headerRow.appendChild(th);
    }
    );
    
    data.reeds.forEach(reed => {
        let row = rec_table.insertRow(-1);
        row.classList.add("reed-rows");
        let id = row.insertCell(0);
        let type = row.insertCell(1);
        let health_score = row.insertCell(2);
        let rested = row.insertCell(3);
        
        let options = row.insertCell(4);
        //creates an options button for each reed using direct html, since we don't know directly the number of reeds
        //the is is reed.id + "-options" to make it easily accessible for accessing
        options.innerHTML = `<button id=${reed.id + "-options"} class='options-btn'><img id=${reed.id + "-options-img"} class='options-img' src='/static/marks/options.png'></button>`;
        document.getElementById(reed.id + "-options").addEventListener("click", () => {openMenuPopup(reed.id + "-options")});

        id.innerHTML = reed.id;
        type.innerHTML = reed.reed_type;
        health_score.innerHTML = reed.health_score;
        //loads a different image depending on if the reed is rested; check if rested, x if not rested
        rested.innerHTML = reed.is_rested ? "<img id='check' class='check-mark' src='/static/marks/check.png' alt='check'>" : "<img id='x' class='x-mark' src='/static/marks/x.png' alt='x mark'>";
    });

}

async function load_best_reeds() {
    /**
     * Loads the best break-in reed and the recommended reed from the database.
     * Outputs on the home screen.
     */
    const data = await getReedData();
    let best_breakin;
    let best_reed;
    //in order for a reed to be the best reed, it can either be rested and at the highest health
    //or if no reeds are rested, it can just have the highest health score
    //for break-in reeds, it is just sorted by the amount of days rested
    data.reeds.forEach(reed => {
        if (reed.step) {
            if (!best_breakin || (reed.days_last_played > best_breakin)) {
                best_breakin = reed;
            }
        } else {
            if (!best_reed || (reed.is_rested && !best_reed.is_rested) || (reed.health_score > best_reed.health_score && (reed.is_rested && best_reed.is_rested || !reed.is_rested && !best_reed.is_rested))) {
                best_reed = reed;
        }
    }
    })
    //if no reed is present, the site should display 'None' after the header instead of leaving it blank
    best_reed_element.innerHTML = best_reed ? `⭐️Best Reed: ${best_reed.id}` : `⭐️Best Reed: None`;
    best_breakin_element.innerHTML = best_breakin ? `🌱Best Break-In Reed: ${best_breakin.id}` : `🌱Best Break-In Reed: None`;
}



function openPopup(popup){
    /**
     * Opens the specified popup to animate it.
     * @param {HTMLElement} popup
     */
    popup.classList.add("open-popup");
}

function closePopup(popup){
    /**
     * Closes the specified popup to remove it from the screen
     * @param {HTMLElement} popup
     */
    popup.classList.remove("open-popup");
}

function openMenuPopup(btn_id) {
    /**
     * Opens the options menu popup for the designated reed clicked.
     * @param {string} btn_id
     */
    //ensures that only one click at a time can go through
    //otherwise, another click would interfere and change the activeListener, so the original never gets removed
    if (closedEventListener) {
        const btn = document.getElementById(btn_id);
        btn_clicked = btn;
        const btn_rect = btn.getBoundingClientRect();
        menu.style.display = "flex";
        menu_delete.style.display = "flex";
        menu_view.style.display = "flex"
        //accounts for gaps and places the menu at the bottom right corner of the button
        menu.style.top = `${btn_rect.top + (btn_rect.height/2) + 10}px`;
        menu.style.left = `${btn_rect.left + (btn_rect.width*2) + 4}px`;

        //uses activeListener to track and remove the menu after it is closed
        activeListener = (event) => {
            handleOutsideClick(event, menu);
        }
        document.addEventListener('click', activeListener);
        closedEventListener = false;
        stopFunctions(); 
}
}

function closeMenuPopup() {
    /**
     * Closes the menu popup for the designated reed stored in the activeListener.
     */
    document.removeEventListener('click', activeListener);
    //sets closedEventListener to true, to allow the user to click another options button
    closedEventListener = true;
    menu.style.display = "none";
    menu_delete.style.display = "none";
    menu_view.style.display = "none"
    continueFunctions();
}

function openDeletePopup() {
    /**
     * Opens the delete menu, only if the popup is still open. 
     */
    if (!closedEventListener) {
        closeMenuPopup();
        openPopup(deletePopup);
        //loads the delete prompt to the user to match the name of the reed to delete
        deleteHeader.innerHTML = `Are you sure you want to delete ${(btn_clicked.id).replace("-options", "")}?`;
    }
}


async function deleteReed() {
    /**
     * Deletes the reed from the database via fetch.
     */
    closePopup(deletePopup);
    await fetch('/delete-reed',
        {"method": "POST",
         "headers": {
            "Content-Type": "application/json"
         },
         //retrieves the reed_id from the format set when creating the button, to send it to app.py to delete from the database
         "body": JSON.stringify({"reed": btn_clicked.id.replace("-options", "")})
        }
        ) 
        .then(response => 
            {if (!response.ok) {
                console.error('Server responded with an error status:', response.status);
            } else {
                console.log('Session saved successfully!');
            }})
        refreshTables();
        }


async function viewReed() {
    /**
     * Opens the viewPopup to display the details about the reed clicked.
     * Fetch used to get the reed from the the database
     */
    if (!closedEventListener) {
        openPopup(viewPopup);
        closeMenuPopup();
        //sends the reed id as a parameter, to get the reed using GET and send its id.
        let reed_data;
        await fetch(`/get-reed/${btn_clicked.id.replace("-options", "")}`)
            .then(response => response.json())
            .then(data => {
                reed_data = data; 
                })
            .catch(error => console.error('Error fetching data: ', error));

        
        const reed = reed_data['reed'][0];
        //uses slice to remove the unnecessary hour, minute, and second details of the date.
        viewPopupText.innerHTML = `ID: ${reed.id} <br>
                            Type: ${reed.reed_type} <br>
                            Strength: ${reed.strength} <br>
                            Health Score: ${reed.health_score} <br>
                            Step: ${reed.step ? reed.step : "Broken In"} <br>
                            Days Rested: ${reed.days_last_played} <br>
                            Minutes Played: ${reed.minutes_played} <br>
                            Break-In Date: ${reed.break_in_date.slice(0, reed.break_in_date.indexOf("T"))} <br>
                            Number of Sessions: ${reed.sessions.length}`;

    }
}

async function processReed(event) {
    /**
     * Proccesses the reed once the user presses submit to ensure valid input and display errors before submitting
     * @param {string} event
     */
    //ensures that the page doesn't refresh 
    if (event) event.preventDefault()
    removeErrorMessages(errors);
    let id = document.getElementById("reed-id").value.trim();
    let strength = document.getElementById("reed-strength").value.trim();
    let reedType = document.getElementById("reed-type").value.trim();
    //await the response from reedExists before continuing to make sure the variable contains data
    const exists = await reedExists(id);

    //the user has to fill out all the fields before continuing to avoid TypeErrors and blanks
    if (!(id && strength && reedType)) {
        errorBlank.style.visibility = "visible";
        errorBlank.style.display = "block";
        return;
    } 
    
    //makes sure the reed doesn't already exist in thte database
    else if (exists){
        errorExists.style.visibility = "visible";
        errorExists.style.display = "block";
        return;
    }
    
    //makes sure that the strength is a number to avoid a TypeError
    else if (!(Number(strength))) {
        errorType.style.visibility = "visible";
        errorType.style.display = "block";
        return;
    }
    else {
        //adds the row to a table, resets the popup, and reloads the webpage to prepare for next action
        addRowFromInput();
        closePopup(reedPopup);
        removeErrorMessages(errors);
        refreshTables();
        return;
    }
    

}

function removeErrorMessages(the_errors) {
    /**
     * Hides error message from the list given.
     * @param {Array} the_errors
     */
    the_errors.forEach (error => {
        error.style.visibility = "hidden";
        //used so that invisible elements don't take up any space
        error.style.display = "none";
    })
}

function handleOutsideClick(event, menu) {
    /**
     * Handles a click to decide whether to close the popup or keep it open.
     * If a user clicks outside the menu, it should close.
     * @param {string} event
     * @param {HTMLElement} menu
     */
    //makes sure that where the user clicks is not the original button or the popup
    if (!menu.contains(event.target) && !btn_clicked.contains(event.target)) {
            closeMenuPopup();
        }
}

function stopFunctions() {
    /**
     * Stops regular website functionality to ensure the other options menus don't appear on hover.
     */
    //makes sure the user can't scroll after pressing the button and that the other options buttons don't appear
    break_in_box.style.overflowY = 'hidden';
    rec_box.style.overflowY = 'hidden';
    btn_clicked.style.visibility = "visible";
    document.getElementById(btn_clicked.id + "-img").style.visibility = "visible";

    const all_rows = [...rec_table.rows, ...break_in_table.rows];
    all_rows.forEach(row => {
        row.classList.remove("reed-rows");
    })

}

function continueFunctions() {
    /**
     * Continues regular website functionality to ensure the user can scroll the table and see the other options.
     */
    //makes sure the user can scroll after clicking away
    break_in_box.style.overflowY = 'auto';
    rec_box.style.overflowY = 'auto';
    btn_clicked.style.visibility = "";
    document.getElementById(btn_clicked.id + "-img").style.visibility = "";

    const rec_table = document.getElementById('rec-table');
    const break_in_table = document.getElementById('break-in-table');
    const all_rows = [...rec_table.rows, ...break_in_table.rows];
    //remove visibility rules
    all_rows.forEach(row => {
        row.classList.add("reed-rows");
    })
}

async function reedExists(id) {
    /**
     * Finds the reed object based on the reed id given using fetch.
     * @param {string} id
     * @return {boolean}
     */
    let exists = false;
    let reedData = null;
    reedData = await getReedData();
    reedData.reeds.forEach(reed => {
        curId = reed.id;
        if (curId == id) {
            exists = true;
        }
    });
    
    return exists;
}

function resetFaces(){
    //resets face buttons to be unselected
    btns.forEach(btn => {
        btn.classList.remove("session-face-btn-selected")
    });
}
function selectFace(id) {
    /**
     * Selects the face button that the user clicks based on the button id.
     * @param {string} id
     */
    let selectedBtn = document.getElementById(id);
    resetFaces()
    selectedBtn.classList.add("session-face-btn-selected");
}

function checkIfSelected() {
    /**
     * Checks if any of the face buttons are selected in order to prevent the user from submitting nothing.
     * @return {HTMLElement | undefined}
     */
    let selected;
    btns.forEach(btn => {
        if (btn.classList.contains('session-face-btn-selected')) {
            selected = btn;
        }
    })
    return selected;
}


function returnWordRating(btn_id) {
    /**
     * Returns the predefined word rating based on the id of the face button pressed.
     * @param {string} btn_id
     * @return {string | null}
     */
    if (btn_id == "happy-face-btn") {
        return "good";
    }
    else if (btn_id == "ok-face-btn") {
        return "ok";
    }
    else if (btn_id == "sad-face-btn") {
        return "bad";
    }
    else {
        return null;
    }
}
async function submitSession(event) {
    /**
     * Submits session information using fetch to the database.
     * Ensures that the session information is valid and updates the reed data accordingly.
     * @param {string} event
     */
    if (event) event.preventDefault();
    //resets error messages to avoid incorrect messages appearing
    removeErrorMessages(sessionErrors);
    let selectedItem = checkIfSelected();
    let id = document.getElementById("reed-choice").value.trim();
    let reedExist = await reedExists(id);
    let minutes = document.getElementById("minutes").value.trim();
    let rating;

    //the user has to select a face in order to rate their session, if not an error message appears
    if (!selectedItem) {
        notSelected.style.visibility = "visible";
        notSelected.style.display = "block";
    }
    //the user cannot leave any input fields blank
    else if(!(id || minutes)) {
        blank.style.visibility = "visible";
        blank.style.display = "block";
    }
    //the reed should exist in the database in order to add a session to it
    else if (!reedExist) {
        idNotValid.style.visibility = "visible";
        idNotValid.style.display = "block";
    }
    //ensures that minutes is a number to avoid a TypeError
    else if (!Number(minutes)){
        notInt.style.visibility = "visible";
        notInt.style.display = "block";
    }
    else {
        //resets the form for the next time the user opens it
        closePopup(sessionPopup);
        resetFaces();
        removeErrorMessages(sessionErrors);
        document.getElementById('reed-choice').value = "";
        document.getElementById('minutes').value = "";

        //post request to app.py to save the session data once submitted
        //gets the rating depending on what button was pressed
        let rating_btn = selectedItem.id;
        let rating = returnWordRating(String(rating_btn));

        const obj_format = {
            "reed_id": id,
            "rating": rating,
            "minutes_played": minutes
        };

        await fetch('/save-session-data',
        {"method": "POST",
         "headers": {
            "Content-Type": "application/json"
         },
         "body": JSON.stringify(obj_format)
        }
        ) 
        .then(response => 
            {if (!response.ok) {
                console.error('Server responded with an error status:', response.status);
            } else {
                console.log('Session saved successfully!');
            }})
        refreshTables();
    }
        };



//adding click actions for all buttons to make them responsive
document.getElementById("reed-popup-submit-btn").addEventListener("click", processReed);
document.getElementById("reed-popup-close-btn").addEventListener("click", () => {closePopup(reedPopup)});
document.getElementById("add-btn").addEventListener("click", () => {openPopup(reedPopup)});

document.getElementById("add-session-btn").addEventListener("click", () => {openPopup(sessionPopup)});
document.getElementById("session-popup-close-btn").addEventListener("click", () => {closePopup(sessionPopup)});
happyBtn.addEventListener("click", () => {selectFace("happy-face-btn")});
okBtn.addEventListener("click", () => {selectFace("ok-face-btn")});
sadBtn.addEventListener("click", () => {selectFace("sad-face-btn")});
document.getElementById("submit-session").addEventListener("click", submitSession);

document.getElementById("no-delete").addEventListener("click", () => {closePopup(deletePopup)});
document.getElementById("yes-delete").addEventListener("click", () => {deleteReed()});
document.getElementById("options-menu-delete").addEventListener("click", () => {openDeletePopup()});

document.getElementById("options-menu-view").addEventListener("click", viewReed);
document.getElementById("view-popup-close-btn").addEventListener("click", () => {closePopup(viewPopup)});

document.getElementById("help-btn").addEventListener("click", () => {openPopup(helpPopup)});
document.getElementById("help-close-btn").addEventListener("click", () => {closePopup(helpPopup)});