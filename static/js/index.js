//path: /static/js/index.js

let tooltips = {};
let isUnsaved = false;

// Fetch the tooltips.json dynamically
async function fetchTooltips() {
    try {
        const response = await fetch("/static/json/tooltips.json");
        tooltips = await response.json();
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

// Fetch and populate available configurations
async function fetchConfigs() {
    try {
        const response = await fetch("/config/list_configs"); // Adjusted route
        const { configs } = await response.json();
        const configSelect = document.getElementById("config-select");
        configSelect.innerHTML = '<option value="default">Default</option>';
        configs.forEach((config) => {
            const option = document.createElement("option");
            option.value = config;
            option.textContent = config;
            configSelect.appendChild(option);
        });
    } catch (error) {
        console.error("Failed to fetch configurations:", error);
    }
}

// Track unsaved changes
function markUnsaved() {
    const configSelect = document.getElementById("config-select");
    const currentConfig = configSelect.value;

    if (!isUnsaved) {
        if (currentConfig === "default") {
            const unsavedOption = document.createElement("option");
            unsavedOption.value = "unsaved";
            unsavedOption.textContent = "Unsaved";
            configSelect.appendChild(unsavedOption);
            configSelect.value = "unsaved";
        } else if (!currentConfig.includes("~unsaved~")) {
            const unsavedOption = document.createElement("option");
            unsavedOption.value = `${currentConfig} ~unsaved~`;
            unsavedOption.textContent = `${currentConfig} ~unsaved~`;
            configSelect.appendChild(unsavedOption);
            configSelect.value = `${currentConfig} ~unsaved~`;
        }
        isUnsaved = true;
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
        const response = await fetch("/config/load_default_config"); // Adjusted route
        const { config } = await response.json();

        // Populate UI fields with the default configuration
        Object.entries(config.hyperparameters || {}).forEach(([key, value]) => {
            const input = document.querySelector(`[name="hyperparameters[${key}]"]`);
            if (input) input.value = value;
        });

        Object.entries(config.training_config || {}).forEach(([key, value]) => {
            const input = document.querySelector(`[name="training_config[${key}]"]`);
            if (input) input.value = value;
        });

        // Clear wrapper and callback checkboxes
        const wrapperCheckboxes = document.querySelectorAll(".wrapper-checkbox");
        const callbackCheckboxes = document.querySelectorAll(".callback-checkbox");

        wrapperCheckboxes.forEach((checkbox) => (checkbox.checked = false));
        callbackCheckboxes.forEach((checkbox) => (checkbox.checked = false));

        alert("Default configuration loaded successfully.");
        isUnsaved = false;
    } catch (error) {
        console.error("Error loading default configuration:", error);
        alert("Failed to load default configuration.");
    }
}

// Load a selected configuration
document.getElementById("load-config").onclick = async () => {
    const configName = document.getElementById("config-select").value;

    if (configName === "default") {
        await loadDefaultConfig();
        return;
    }

    try {
        const response = await fetch(`/config/load_config/${configName}`); // Adjusted route
        const { config } = await response.json();

        // Populate UI fields with the loaded configuration
        Object.entries(config.hyperparameters || {}).forEach(([key, value]) => {
            const input = document.querySelector(`[name="hyperparameters[${key}]"]`);
            if (input) input.value = value;
        });

        Object.entries(config.training_config || {}).forEach(([key, value]) => {
            const input = document.querySelector(`[name="training_config[${key}]"]`);
            if (input) input.value = value;
        });

        // Update wrapper and callback checkboxes
        const wrapperCheckboxes = document.querySelectorAll(".wrapper-checkbox");
        const callbackCheckboxes = document.querySelectorAll(".callback-checkbox");

        wrapperCheckboxes.forEach((checkbox) => {
            checkbox.checked = config.wrappers.includes(checkbox.dataset.key);
        });

        callbackCheckboxes.forEach((checkbox) => {
            checkbox.checked = config.callbacks.includes(checkbox.dataset.key);
        });

        alert(`Configuration '${configName}' loaded successfully.`);
        isUnsaved = false;
    } catch (error) {
        console.error("Error loading configuration:", error);
        alert("Failed to load configuration.");
    }
};

// Save the current configuration
document.getElementById("save-changes").onclick = async () => {
    const configSelect = document.getElementById("config-select");
    const currentConfig = configSelect.value;

    if (currentConfig === "default") {
        alert("Cannot overwrite the Default configuration.");
        return;
    }

    let configName;
    if (currentConfig === "unsaved" || currentConfig.includes("~unsaved~")) {
        configName = prompt("Enter a name for the new configuration:");
    } else {
        const update = confirm("Do you want to update this configuration?");
        configName = update ? currentConfig.replace(" ~unsaved~", "") : prompt("Enter a name for the new configuration:");
    }

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

    // Gather data from the UI
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
        const response = await fetch("/config/save_config", { // Adjusted route
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });

        const result = await response.json();
        alert(result.message);

        await fetchConfigs(); // Refresh the config list

        // Auto-select the newly saved configuration
        configSelect.value = configName;
        isUnsaved = false; // Reset unsaved state
    } catch (error) {
        console.error("Error saving configuration:", error);
        alert("Failed to save configuration.");
    }
};

// Delete a selected configuration
document.getElementById("delete-config").onclick = async () => {
    const configName = document.getElementById("config-select").value;

    if (configName === "default") {
        alert("Cannot delete the Default configuration.");
        return;
    }

    try {
        const response = await fetch(`/config/delete_config/${configName}`, { method: "DELETE" }); // Adjusted route
        const result = await response.json();
        alert(result.message);
        await fetchConfigs(); // Refresh the config list
    } catch (error) {
        console.error("Error deleting configuration:", error);
        alert("Failed to delete configuration.");
    }
};

// Initialize log streaming for training logs
function initializeLogStreaming() {
    const logOutput = document.getElementById("training-logs");
    if (!logOutput) {
        console.warn("Log output element not found.");
        return;
    }

    const eventSource = new EventSource("/stream/logs"); // Adjusted route
    eventSource.onmessage = (event) => {
        const newLogEntry = document.createElement("div");
        newLogEntry.textContent = event.data;
        logOutput.appendChild(newLogEntry);
        logOutput.scrollTop = logOutput.scrollHeight; // Auto-scroll to the bottom
    };
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


// Initialize index-specific logic
document.addEventListener("DOMContentLoaded", async () => {
    await fetchTooltips();
    await fetchConfigs(); // Load available configurations
    initializeLogStreaming();
    initializeVideoFeed();
    addChangeListeners(); // Track changes for unsaved state
});


document.addEventListener("DOMContentLoaded", () => {
    const nStepsInput = document.querySelector(`[name="hyperparameters[n_steps]"]`);
    const numEnvsInput = document.querySelector(`[name="training_config[num_envs]"]`);
    const batchSizeSelect = document.getElementById("batch-size-select");

    if (!nStepsInput || !numEnvsInput || !batchSizeSelect) {
        console.error("Batch size, n_steps, or num_envs input is missing in the DOM.");
        return;
    }

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

    function populateBatchSizeDropdown() {
        const nSteps = parseInt(nStepsInput.value, 10);
        const numEnvs = parseInt(numEnvsInput.value, 10);

        console.log(`Populating batch size dropdown: n_steps=${nSteps}, num_envs=${numEnvs}`);

        if (isNaN(nSteps) || isNaN(numEnvs)) {
            console.error("n_steps or num_envs is not a valid number.");
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
});

