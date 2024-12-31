// path: /static/js/metrics_dashboard.js

/**
 * Fetch and initialize metrics for the dashboard.
 */
async function fetchMetricsData() {
    try {
        const response = await fetch("/metrics/data"); // API to fetch metrics
        if (!response.ok) throw new Error("Failed to fetch metrics data.");

        const metricsData = await response.json();
        populateMetricsCharts(metricsData);
        console.log("Metrics data fetched and charts updated.");
    } catch (error) {
        console.error("Error fetching metrics data:", error);
    }
}

/**
 * Populate and update all dashboard metrics.
 * @param {Object} data Metrics data from the server
 */
function populateMetricsCharts(data) {
    // Extract relevant metrics
    const monitorRewards = Object.values(data.env0 || {}).reduce((a, b) => a + b, 0);
    const trainingRewards = Object.values(data.training || {}).reduce((a, b) => a + b, 0);

    // Update the Reward Comparison Meter
    updateRewardComparisonMeter(monitorRewards, trainingRewards);

    // Update other charts
    updateLineChart("env0-line-chart", "Monitor Env - Line Chart", data.env0);
    updateLineChart("training-line-chart", "Training - Line Chart", data.training);
    updateRewardDistributionChart("env0-reward-chart", "Monitor Env - Reward Distribution", data.rewardDistribution);
    updateRewardDistributionChart("training-reward-chart", "Training - Reward Distribution", data.rewardDistribution);

    // Update placeholders
    updatePlaceholderChart("env0-placeholder-chart", "Monitor Env - Placeholder");
    updatePlaceholderChart("training-placeholder-chart", "Training - Placeholder");
}


/**
 * Update a line chart with metrics data.
 * @param {string} chartId ID of the canvas element for the chart
 * @param {string} label Label for the chart
 * @param {Object} metrics Metrics data for the chart
 */
function updateLineChart(chartId, label, metrics) {
    const ctx = document.getElementById(chartId).getContext("2d");
    const labels = Object.keys(metrics).map((key) => `Step ${key}`);
    const values = Object.values(metrics);

    new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label,
                    data: values,
                    borderColor: "blue",
                    borderWidth: 2,
                },
            ],
        },
    });
}

/**
 * Update a reward distribution pie chart.
 * @param {string} chartId ID of the canvas element for the chart
 * @param {string} label Label for the chart
 * @param {Object} distribution Reward distribution data
 */
function updateRewardDistributionChart(chartId, label, distribution) {
    const ctx = document.getElementById(chartId).getContext("2d");
    const labels = Object.keys(distribution);
    const values = Object.values(distribution);

    new Chart(ctx, {
        type: "pie",
        data: {
            labels,
            datasets: [
                {
                    label,
                    data: values,
                    backgroundColor: ["gold", "silver", "gray"],
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
    const monitorPercentage = (monitorReward / totalReward) * 100;

    // Update the position of the tick
    const tick = document.getElementById("reward-meter-tick");
    if (tick) {
        tick.style.left = `${monitorPercentage}%`;
        console.log(`Meter Updated: Monitor (${monitorReward}) vs Training (${trainingReward})`);
    }
}

/**
 * Update a placeholder chart.
 * @param {string} chartId ID of the canvas element for the chart
 * @param {string} label Label for the placeholder
 */
function updatePlaceholderChart(chartId, label) {
    const ctx = document.getElementById(chartId).getContext("2d");
    new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Placeholder"],
            datasets: [
                {
                    label,
                    data: [1],
                    backgroundColor: ["gray"],
                },
            ],
        },
    });
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

    // Ensure placeholder is visible by default
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
                setTimeout(checkRenderStatus, 1000); // Retry every second
            }
        } catch (error) {
            console.error("Error checking render status:", error);
            setTimeout(checkRenderStatus, 1000); // Retry in case of error
        }
    };

    checkRenderStatus();
}

/**
 * Initialize listeners for Metrics Dashboard.
 */
function initializeListenersForMetricsDashboard() {
    initializeVideoFeed();
    fetchMetricsData();
    console.log("Listeners for Metrics Dashboard initialized.");
}

// Event listener for when the Metrics Dashboard is loaded dynamically
document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname.includes("/dashboard/metrics")) {
        initializeListenersForMetricsDashboard();
    }
});
