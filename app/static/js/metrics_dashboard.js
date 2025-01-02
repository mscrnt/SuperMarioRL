/**
 * Fetch and initialize metrics for the dashboard.
 * @param {Array<string>} statKeys List of stats to fetch
 * @param {string} groupBy Column to group the stats by (default is "step")
 */
async function fetchMetricsData(statKeys, groupBy = "step") {
    try {
        const queryParams = new URLSearchParams();
        queryParams.append("group_by", groupBy);
        statKeys.forEach((key) => queryParams.append("stat_keys", key));

        const response = await fetch(`/metrics/data?${queryParams.toString()}`);
        if (!response.ok) throw new Error("Failed to fetch metrics data.");

        const metricsData = await response.json();
        populateMetricsCharts(metricsData, statKeys);
        console.log("Metrics data fetched and charts updated.");
    } catch (error) {
        console.error("Error fetching metrics data:", error);
        populateMetricsCharts({}, statKeys); // Fallback with empty data
    }
}

/**
 * Populate and update all dashboard metrics.
 * @param {Object} data Metrics data from the server
 * @param {Array<string>} statKeys List of stats being tracked
 */
function populateMetricsCharts(data, statKeys) {
    statKeys.forEach((stat) => {
        const monitorData = data.env0Stats?.[stat] || {};
        const trainingData = data.trainingStats?.[stat] || {};

        console.log(`Processing stat: ${stat}`);
        console.log("Monitor Data:", monitorData);
        console.log("Training Data:", trainingData);

        // Update charts for the current stat
        destroyAndUpdateChart(
            `env0-${stat}-chart`,
            `Monitor Env - ${stat}`,
            monitorData,
            "line"
        );
        destroyAndUpdateChart(
            `training-${stat}-chart`,
            `Training - ${stat}`,
            trainingData,
            "line"
        );

        // Special handling for Kill/Death Ratio
        if (stat === "enemy_kills" || stat === "deaths") {
            calculateAndDisplayKD(data);
        }
    });

    // Reward Comparison Meter (if "reward" is included)
    if (statKeys.includes("reward")) {
        const monitorRewards = Object.values(data.env0Stats?.reward || {}).reduce((a, b) => a + b, 0);
        const trainingRewards = Object.values(data.trainingStats?.reward || {}).reduce((a, b) => a + b, 0);

        console.log(`Monitor Rewards: ${monitorRewards}`);
        console.log(`Training Rewards: ${trainingRewards}`);

        updateRewardComparisonMeter(monitorRewards, trainingRewards);
    }
}


/**
 * Refresh metrics periodically.
 * @param {Array<string>} statKeys List of stats to fetch
 * @param {number} interval Refresh interval in milliseconds (default 10 seconds)
 */
function startMetricsRefresh(statKeys, interval = 10000) {
    fetchMetricsData(statKeys); // Fetch immediately on page load
    setInterval(() => fetchMetricsData(statKeys), interval); // Refresh periodically
}
/**
 * Calculate and display the K/D ratio for monitor and training environments.
 * @param {Object} data Metrics data from the server
 */
function calculateAndDisplayKD(data) {
    const monitorKills = Object.values(data.env0Stats?.enemy_kills || {}).reduce((a, b) => a + b, 0);
    const monitorDeaths = Object.values(data.env0Stats?.deaths || {}).reduce((a, b) => a + b, 0);
    const monitorKD = monitorDeaths > 0 ? (monitorKills / monitorDeaths).toFixed(2) : "Infinity";

    const trainingKills = Object.values(data.trainingStats?.enemy_kills || {}).reduce((a, b) => a + b, 0);
    const trainingDeaths = Object.values(data.trainingStats?.deaths || {}).reduce((a, b) => a + b, 0);
    const trainingKD = trainingDeaths > 0 ? (trainingKills / trainingDeaths).toFixed(2) : "Infinity";

    console.log(`Monitor K/D: ${monitorKills}/${monitorDeaths} = ${monitorKD}`);
    console.log(`Training K/D: ${trainingKills}/${trainingDeaths} = ${trainingKD}`);

    updateKDDisplay("env0-kd-display", "Monitor K/D", monitorKD);
    updateKDDisplay("training-kd-display", "Training K/D", trainingKD);
}

/**
 * Display K/D Ratio as a float.
 * @param {string} elementId ID of the element where the K/D should be displayed
 * @param {string} label Label for the display
 * @param {string} kdRatio The calculated K/D ratio
 */
function updateKDDisplay(elementId, label, kdRatio) {
    const container = document.getElementById(elementId);
    if (container) {
        container.innerHTML = `<h2>${label}</h2><p>${kdRatio}</p>`;
        console.log(`Updated ${label} to ${kdRatio}`);
    }
}

/**
 * Destroy an existing chart and recreate it with new data.
 * @param {string} chartId ID of the canvas element for the chart
 * @param {string} label Label for the chart
 * @param {Object} data Data for the chart
 * @param {string} type Chart type (e.g., "line", "pie", "bar")
 */
function destroyAndUpdateChart(chartId, label, data, type) {
    const ctx = document.getElementById(chartId)?.getContext("2d");
    if (!ctx) return;

    if (window.charts && window.charts[chartId]) {
        window.charts[chartId].destroy();
    } else {
        if (!window.charts) window.charts = {};
    }

    const labels = Object.keys(data).map((key) => `Step ${key}`);
    const values = Object.values(data);

    window.charts[chartId] = new Chart(ctx, {
        type,
        data: {
            labels,
            datasets: [
                {
                    label,
                    data: values,
                    borderColor: "blue",
                    borderWidth: 2,
                    backgroundColor: type === "pie" ? ["gold", "silver", "gray"] : undefined,
                },
            ],
        },
    });
}

/**
 * Update the reward comparison meter.
 * @param {number} monitorReward Total rewards for Monitor Env
 * @param {number} trainingReward Total rewards for Training Envs
 */
function updateRewardComparisonMeter(monitorReward, trainingReward) {
    const totalReward = monitorReward + trainingReward;
    const monitorPercentage = totalReward > 0 ? (monitorReward / totalReward) * 100 : 50; // Default to 50%

    const tick = document.getElementById("reward-meter-tick");
    if (tick) {
        tick.style.left = `${monitorPercentage}%`;
        console.log(`Meter Updated: Monitor (${monitorReward}) vs Training (${trainingReward})`);
    }
}

/**
 * Initialize video feed logic with placeholder.
 */
function initializeVideoFeed() {
    const videoPlaceholder = document.getElementById("video-placeholder");
    const videoFeed = document.getElementById("video-feed");

    if (!videoPlaceholder || !videoFeed) {
        console.error("Video elements are missing in the DOM.");
        return;
    }

    videoPlaceholder.style.display = "block";
    videoFeed.style.display = "none";

    const checkRenderStatus = async () => {
        try {
            const response = await fetch("/training/render_status");
            const { rendering } = await response.json();

            if (rendering) {
                videoPlaceholder.style.display = "none";
                videoFeed.style.display = "block";
            } else {
                setTimeout(checkRenderStatus, 1000);
            }
        } catch (error) {
            console.error("Error checking render status:", error);
            setTimeout(checkRenderStatus, 1000);
        }
    };

    checkRenderStatus();
}

/**
 * Initialize listeners for Metrics Dashboard.
 */
function initializeListenersForMetricsDashboard() {
    const statKeys = ["enemy_kills", "deaths", "reward"]; // Specify the stats you want to track
    initializeVideoFeed();
    startMetricsRefresh(statKeys);
    console.log("Listeners for Metrics Dashboard initialized.");
}

// Event listener for when the Metrics Dashboard is loaded dynamically
document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname.includes("/dashboard/metrics")) {
        initializeListenersForMetricsDashboard();
    }
});
