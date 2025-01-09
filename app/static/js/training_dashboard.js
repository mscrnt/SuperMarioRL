//path: /static/js/training_dashboard.js

let tooltips = {};

// Fetch the tooltips.json dynamically
async function fetchTooltips() {
    try {
        const response = await fetch("/static/json/tooltips.json");
        Object.assign(tooltips, await response.json());
        console.log("Tooltips loaded successfully.");
    } catch (error) {
        console.error("Failed to fetch tooltips:", error);
    }
}

// Open the tooltip modal
function openModal(key) {
    const modal = document.getElementById("tooltip-modal");
    if (!modal) {
        console.error("Tooltip modal not found in the DOM.");
        return;
    }

    const titleElement = modal.querySelector("#modal-title");
    const descriptionElement = modal.querySelector("#modal-description");
    const exampleElement = modal.querySelector("#modal-example");
    const proTipElement = modal.querySelector("#modal-pro-tip");

    if (!titleElement || !descriptionElement || !exampleElement || !proTipElement) {
        console.error("Modal elements are missing in the DOM.");
        return;
    }

    const tooltip = tooltips[key];
    if (tooltip) {
        titleElement.innerText = tooltip.title || key.replace("_", " ").toUpperCase();
        descriptionElement.innerText = tooltip.description || "No description available.";
        exampleElement.innerText = tooltip.example || "No example available.";
        proTipElement.innerText = tooltip.proTip || "No pro tip available.";
    } else {
        console.warn(`Tooltip for key "${key}" not found.`);
        titleElement.innerText = key.replace("_", " ").toUpperCase();
        descriptionElement.innerText = "No details available.";
        exampleElement.innerText = "";
        proTipElement.innerText = "";
    }
    modal.style.display = "block";
}

// Close the tooltip modal
function closeModal() {
    const modal = document.getElementById("tooltip-modal");
    if (modal) modal.style.display = "none";
}

// Initialize tooltips and attach event listeners
async function initializeTooltips() {
    await fetchTooltips();

    document.querySelectorAll(".tooltip-icon").forEach((icon) => {
        const key = icon.getAttribute("data-tooltip-key");
        if (key) {
            icon.addEventListener("click", () => openModal(key));
        }
    });

    console.log("Tooltips initialized.");
}

function initializeConfigManager() {
    let isUnsaved = false;

    // Fetch and populate available configurations
    async function fetchConfigs() {
        try {
            const response = await fetch("/config/list_configs");
            const { configs } = await response.json();
            const configSelect = document.getElementById("config-select");

            // Populate dropdown
            configSelect.innerHTML = '<option value="default">Default</option>';
            configs.forEach((config) => {
                const option = document.createElement("option");
                option.value = config;
                option.textContent = config;
                configSelect.appendChild(option);
            });

            console.log("Configurations fetched and populated.");
        } catch (error) {
            console.error("Failed to fetch configurations:", error);
        }
    }

    // Mark configuration as unsaved
    function markUnsaved() {
        const configSelect = document.getElementById("config-select");
        const currentConfig = configSelect.value;

        if (!isUnsaved) {
            let unsavedOption;
            if (currentConfig === "default") {
                unsavedOption = document.createElement("option");
                unsavedOption.value = "unsaved";
                unsavedOption.textContent = "Unsaved";
            } else if (!currentConfig.includes("~unsaved~")) {
                unsavedOption = document.createElement("option");
                unsavedOption.value = `${currentConfig} ~unsaved~`;
                unsavedOption.textContent = `${currentConfig} ~unsaved~`;
            }

            if (unsavedOption) {
                configSelect.appendChild(unsavedOption);
                configSelect.value = unsavedOption.value;
                isUnsaved = true;
            }
        }
    }

    // Add change listeners to inputs
    function addChangeListeners() {
        const inputs = document.querySelectorAll(".config-input, .wrapper-checkbox, .callback-checkbox");
        inputs.forEach((input) => input.addEventListener("change", markUnsaved));
    }

    // Load the default configuration
    async function loadDefaultConfig() {
        try {
            const response = await fetch("/config/load_default_config");
            const { config } = await response.json();
    
            if (response.ok) {
                populateFields(config);
                alert("Default configuration loaded successfully.");
            } else {
                console.error(config.message || "Failed to load default configuration.");
                alert("Failed to load default configuration.");
            }
        } catch (error) {
            console.error("Error loading default configuration:", error);
            alert("Failed to load default configuration.");
        }
    }
    

    // Load a selected configuration
    async function loadSelectedConfig() {
        const configName = document.getElementById("config-select").value;

        if (configName === "default") {
            await loadDefaultConfig();
            return;
        }

        try {
            const response = await fetch(`/config/load_config/${configName}`);
            const { config } = await response.json();

            if (response.ok) {
                populateFields(config);
                alert(`Configuration '${configName}' loaded successfully.`);
            } else {
                console.error(config.message || "Failed to load configuration.");
                alert("Failed to load configuration.");
            }
        } catch (error) {
            console.error("Error loading configuration:", error);
            alert("Failed to load configuration.");
        }
    }

    // Populate the fields with the configuration data
    function populateFields(config) {
        // Populate training config fields
        Object.entries(config.training_config || {}).forEach(([key, value]) => {
            const input = document.querySelector(`[name="training_config[${key}]"]`);
            if (input) {
                if (input.tagName === "SELECT") {
                    input.value = value !== undefined && value !== null ? value.toString() : "False";
                } else {
                    input.value = value !== undefined && value !== null ? value : "";
                }
            }
        });

        // Populate hyperparameters fields
        Object.entries(config.hyperparameters || {}).forEach(([key, value]) => {
            const input = document.querySelector(`[name="hyperparameters[${key}]"]`);
            if (input) {
                if (input.type === "number" && value !== null && value !== undefined) {
                    input.value = parseFloat(value); // Ensure numeric inputs have numeric values
                } else {
                    input.value = value !== undefined && value !== null ? value : "";
                }
            }
        });

        // Populate wrapper checkboxes
        document.querySelectorAll(".wrapper-checkbox").forEach((checkbox) => {
            const wrapperName = checkbox.value;
            checkbox.checked = config.enabled_wrappers?.includes(wrapperName) || checkbox.hasAttribute("disabled");
        });

        // Populate callback checkboxes
        document.querySelectorAll(".callback-checkbox").forEach((checkbox) => {
            const callbackName = checkbox.value;
            checkbox.checked = config.enabled_callbacks?.includes(callbackName) || checkbox.hasAttribute("disabled");
        });

        console.log("Configuration fields populated successfully.");
    }


    // Save the current configuration
    async function saveCurrentConfig() {
        const configSelect = document.getElementById("config-select");
        const currentConfig = configSelect.value;

        if (currentConfig === "default") {
            alert("Cannot overwrite the Default configuration.");
            return;
        }

        let configName = currentConfig.includes("~unsaved~")
            ? currentConfig.replace(" ~unsaved~", "")
            : prompt("Enter a name for the new configuration:");

        if (!configName) return;

        const data = {
            name: configName,
            overwrite: currentConfig.includes("~unsaved~"),
            config: {
                hyperparameters: {},
                training_config: {},
                wrappers: [],
                callbacks: [],
            },
        };

        // Gather data from UI
        document.querySelectorAll(".config-input").forEach((input) => {
            const name = input.name;
            const value = input.value;

            if (name.startsWith("hyperparameters")) {
                data.config.hyperparameters[name.split("[")[1].replace("]", "")] = value;
            } else if (name.startsWith("training_config")) {
                data.config.training_config[name.split("[")[1].replace("]", "")] = value;
            }
        });

        document.querySelectorAll(".wrapper-checkbox:checked").forEach((checkbox) => {
            data.config.wrappers.push(checkbox.dataset.key);
        });

        document.querySelectorAll(".callback-checkbox:checked").forEach((checkbox) => {
            data.config.callbacks.push(checkbox.dataset.key);
        });

        // Save configuration
        try {
            const response = await fetch("/config/save_config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });

            const result = await response.json();
            alert(result.message);

            await fetchConfigs();
            configSelect.value = configName;
            isUnsaved = false;
        } catch (error) {
            console.error("Error saving configuration:", error);
            alert("Failed to save configuration.");
        }
    }

    // Delete a selected configuration
    async function deleteSelectedConfig() {
        const configName = document.getElementById("config-select").value;

        if (configName === "default") {
            alert("Cannot delete the Default configuration.");
            return;
        }

        try {
            const response = await fetch(`/config/delete_config/${configName}`, { method: "DELETE" });
            const result = await response.json();
            alert(result.message);
            await fetchConfigs();
        } catch (error) {
            console.error("Error deleting configuration:", error);
            alert("Failed to delete configuration.");
        }
    }

    // Attach event listeners
    document.getElementById("load-config").onclick = loadSelectedConfig;
    document.getElementById("save-changes").onclick = saveCurrentConfig;
    document.getElementById("delete-config").onclick = deleteSelectedConfig;

    // Initialize configuration manager
    fetchConfigs();
    addChangeListeners();
    console.log("Configuration Manager initialized.");
}


// Initialize log streaming for training logs
function initializeLogStreaming() {
    const logOutput = document.getElementById("training-logs");
    if (!logOutput) {
        console.warn("Log output element not found.");
        return;
    }

    let isUserScrolling = false;

    // Detect if the user is scrolling
    logOutput.addEventListener("scroll", () => {
        const isAtBottom =
            logOutput.scrollHeight - logOutput.scrollTop === logOutput.clientHeight;
        isUserScrolling = !isAtBottom;
    });

    const eventSource = new EventSource("/stream/logs"); // Adjusted route
    eventSource.onmessage = (event) => {
        const newLogEntry = document.createElement("div");
        newLogEntry.textContent = event.data;
        logOutput.appendChild(newLogEntry);

        // Only auto-scroll if the user is not actively scrolling
        if (!isUserScrolling) {
            logOutput.scrollTop = logOutput.scrollHeight;
        }
    };

    // Allow re-enabling auto-scroll when the user scrolls back to the bottom
    const observer = new MutationObserver(() => {
        const isAtBottom =
            logOutput.scrollHeight - logOutput.scrollTop === logOutput.clientHeight;
        if (isAtBottom) {
            isUserScrolling = false; // Re-enable auto-scrolling
        }
    });

    observer.observe(logOutput, { childList: true });
}


// Initialize video feed logic with placeholder
async function initializeVideoFeed() {
    const videoPlaceholder = document.getElementById("video-placeholder");
    const videoFeed = document.getElementById("video-feed");

    if (!videoPlaceholder || !videoFeed) {
        console.error("Video elements are missing in the DOM.");
        return;
    }

    // Ensure placeholder is visible by default
    videoPlaceholder.style.display = "block";
    videoFeed.style.display = "none";

    const checkRenderStatus = async () => {
        try {
            const response = await fetch("/training/render_status"); // Adjusted route
            const { rendering } = await response.json();

            if (rendering) {
                videoPlaceholder.style.display = "none";
                videoFeed.style.display = "block";
            } else {
                setTimeout(checkRenderStatus, 1000); // Retry every second
            }
        } catch (error) {
            console.error("Error checking render status:", error);
            setTimeout(checkRenderStatus, 1000); // Retry in case of error
        }
    };

    checkRenderStatus(); // Start checking rendering status
}




function initializeBatchSizeDropdown() {
    const nStepsInput = document.querySelector(`[name="hyperparameters[n_steps]"]`);
    const numEnvsInput = document.querySelector(`[name="training_config[num_envs]"]`);
    const batchSizeSelect = document.getElementById("batch-size-select");

    if (!nStepsInput || !numEnvsInput || !batchSizeSelect) {
        console.error("Batch size, n_steps, or num_envs input is missing in the DOM.");
        return;
    }

    // Function to calculate valid batch sizes
    function calculateValidBatchSizes(nSteps, numEnvs) {
        console.log(`Calculating valid batch sizes for n_steps: ${nSteps}, num_envs: ${numEnvs}`);
        const totalRollout = nSteps * numEnvs;
        console.log(`Total rollout (n_steps * num_envs): ${totalRollout}`);

        const validBatchSizes = [];
        for (let nMinibatches = 1; nMinibatches <= totalRollout; nMinibatches++) {
            if (totalRollout % nMinibatches === 0) {
                validBatchSizes.push(totalRollout / nMinibatches);
            }
        }

        console.log(`Valid batch sizes: ${validBatchSizes}`);
        return validBatchSizes.sort((a, b) => a - b); // Sort ascending
    }

    // Function to populate the dropdown with valid batch sizes
    function populateBatchSizeDropdown() {
        const nSteps = parseInt(nStepsInput.value, 10);
        const numEnvs = parseInt(numEnvsInput.value, 10);

        console.log(`Populating batch size dropdown: n_steps=${nSteps}, num_envs=${numEnvs}`);

        if (isNaN(nSteps) || isNaN(numEnvs)) {
            console.error("Invalid n_steps or num_envs value.");
            return;
        }

        const validBatchSizes = calculateValidBatchSizes(nSteps, numEnvs);

        // Clear existing options
        batchSizeSelect.innerHTML = "";

        if (validBatchSizes.length) {
            // Populate dropdown with valid batch sizes
            validBatchSizes.forEach((size) => {
                const option = document.createElement("option");
                option.value = size;
                option.textContent = size;
                batchSizeSelect.appendChild(option);
            });

            // Select the largest valid batch size by default
            batchSizeSelect.value = validBatchSizes[validBatchSizes.length - 1];
            console.log(`Default selected batch size: ${batchSizeSelect.value}`);
        } else {
            console.warn("No valid batch sizes available for the given n_steps and num_envs.");
            const defaultOption = document.createElement("option");
            defaultOption.value = "";
            defaultOption.textContent = "No valid batch sizes available";
            defaultOption.disabled = true;
            batchSizeSelect.appendChild(defaultOption);
        }
    }

    // Attach listeners to dynamically update the dropdown
    nStepsInput.addEventListener("input", populateBatchSizeDropdown);
    numEnvsInput.addEventListener("input", populateBatchSizeDropdown);

    // Initialize batch size dropdown based on default values
    console.log("Initializing batch size dropdown...");
    populateBatchSizeDropdown();
}

function toggleStagesTextbox() {
    const randomStagesDropdown = document.querySelector(`[name="training_config[random_stages]"]`);
    const stagesTextbox = document.querySelector(`[name="training_config[stages]"]`);

    if (!randomStagesDropdown || !stagesTextbox) {
        console.error("Random stages dropdown or stages textbox not found.");
        return;
    }

    const updateTextboxState = () => {
        const isRandomStages = randomStagesDropdown.value === "True";

        // Enable/Disable the textbox
        stagesTextbox.disabled = !isRandomStages;

        // Add hover text and grey-out style when disabled
        if (!isRandomStages) {
            // stagesTextbox.value = ""; // Clear the value when disabled
            stagesTextbox.style.cursor = "not-allowed"; // Cursor indicates not clickable
            stagesTextbox.title = "Enable 'Random Stages' to modify stages."; // Hover text
        } else {
            stagesTextbox.style.backgroundColor = ""; // Reset background color
            stagesTextbox.style.cursor = ""; // Reset cursor
            stagesTextbox.title = ""; // Remove hover text
        }
    };

    // Initialize the state on page load
    updateTextboxState();

    // Add event listener for changes
    randomStagesDropdown.addEventListener("change", updateTextboxState);
}

async function initializeShaderToggles() {
    const shaderToggles = {
        all: document.getElementById("shader-all-toggle"),
        radial_distortion: document.getElementById("shader-radial-distortion"),
        scanlines: document.getElementById("shader-scanlines"),
        dot_mask: document.getElementById("shader-dot-mask"),
        rolling_lines: document.getElementById("shader-rolling-lines"),
        gamma_correction: document.getElementById("shader-gamma-correction"),
    };

    if (Object.values(shaderToggles).some(toggle => !toggle)) {
        console.error("Some shader toggle elements are missing.");
        return;
    }

    // Fetch initial shader settings
    try {
        const response = await fetch("/training/shader_status");
        const { shaderSettings } = await response.json();

        for (const [key, state] of Object.entries(shaderSettings)) {
            if (shaderToggles[key]) shaderToggles[key].checked = state;
        }

        // Sync "Enable All" toggle state
        shaderToggles.all.checked = Object.values(shaderSettings).every(Boolean);
    } catch (error) {
        console.error("Error fetching shader settings:", error);
    }

    // Add individual toggle listeners
    for (const [key, toggle] of Object.entries(shaderToggles)) {
        if (key === "all") continue;

        toggle.addEventListener("change", async () => {
            try {
                const response = await fetch("/training/toggle_shader", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ key, enabled: toggle.checked }),
                });

                const result = await response.json();
                if (result.success) {
                    console.log(`Shader "${key}" toggled: ${toggle.checked ? "enabled" : "disabled"}`);
                    // Sync "Enable All" checkbox
                    shaderToggles.all.checked = Object.values(shaderToggles).slice(1).every(t => t.checked);
                } else {
                    console.error(`Failed to toggle shader "${key}".`);
                    toggle.checked = !toggle.checked; // Revert on failure
                }
            } catch (error) {
                console.error(`Error toggling shader "${key}":`, error);
                toggle.checked = !toggle.checked; // Revert on error
            }
        });
    }

    // Add "Enable All" listener
    shaderToggles.all.addEventListener("change", async () => {
        const enableAll = shaderToggles.all.checked;

        try {
            const response = await fetch("/training/toggle_shader_all", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ enableAll }),
            });

            const result = await response.json();
            if (result.success) {
                console.log(`All shaders toggled: ${enableAll ? "enabled" : "disabled"}`);
                for (const [key, toggle] of Object.entries(shaderToggles)) {
                    toggle.checked = enableAll;
                }
            } else {
                console.error("Failed to toggle all shaders.");
                shaderToggles.all.checked = !enableAll; // Revert on failure
            }
        } catch (error) {
            console.error("Error toggling all shaders:", error);
            shaderToggles.all.checked = !enableAll; // Revert on error
        }
    });
}



function initializeListenersForTrainingDashboard() {
    // Initialize configuration manager
    initializeConfigManager();

    // Initialize tooltips
    initializeTooltips();

    // Initialize log streaming
    initializeLogStreaming();

    // Initialize video feed
    initializeVideoFeed();

    // Initialize batch size dropdown
    initializeBatchSizeDropdown();

    // Initialize random stages toggle
    toggleStagesTextbox();

    // Initialize CRT shader toggle
    initializeShaderToggles();

    console.log("Listeners for Training Dashboard initialized.");
}
