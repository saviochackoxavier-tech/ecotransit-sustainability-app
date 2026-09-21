/**
 * Client-side journey tracking: start/stop a journey and log GPS points
 * against the Phase 4 JSON API, and render them on a Leaflet map.
 *
 * Vanilla JS (ES6+), per the spec's tech stack (§2) — no frontend
 * framework.
 */
(() => {
    "use strict";

    const setupPanel = document.getElementById("setup-panel");
    const activePanel = document.getElementById("active-panel");
    const resultPanel = document.getElementById("result-panel");
    const setupError = document.getElementById("setup-error");
    const trackingError = document.getElementById("tracking-error");

    let journeyId = window.ECOTRANSIT_ACTIVE_JOURNEY_ID || null;
    let map = null;
    let polyline = null;
    let watchId = null;
    let pointCount = 0;

    function getCookie(name) {
        const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
        return match ? decodeURIComponent(match[2]) : null;
    }

    async function api(path, options = {}) {
        const response = await fetch(path, {
            method: options.method || "GET",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: options.body ? JSON.stringify(options.body) : undefined,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || `Request to ${path} failed (${response.status}).`);
        }
        return data;
    }

    function showError(el, message) {
        el.textContent = message;
        el.classList.remove("hidden");
    }

    function initMap() {
        map = L.map("map").setView([0, 0], 2);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OpenStreetMap contributors",
            maxZoom: 19,
        }).addTo(map);
        polyline = L.polyline([], { color: "#1F3D2E" }).addTo(map);
    }

    function addPointToMap(lat, lon) {
        const latlng = [lat, lon];
        polyline.addLatLng(latlng);
        map.setView(latlng, Math.max(map.getZoom(), 15));
    }

    async function loadExistingPoints() {
        const data = await api(`/api/journeys/${journeyId}/`);
        (data.journey.points || []).forEach((p) => addPointToMap(parseFloat(p.latitude), parseFloat(p.longitude)));
        pointCount = (data.journey.points || []).length;
        document.getElementById("point-count").textContent = pointCount;
    }

    async function logPoint(lat, lon) {
        try {
            await api(`/api/journeys/${journeyId}/points/`, {
                method: "POST",
                body: { latitude: lat, longitude: lon },
            });
            pointCount += 1;
            document.getElementById("point-count").textContent = pointCount;
            addPointToMap(lat, lon);
        } catch (err) {
            showError(trackingError, err.message);
        }
    }

    function startWatchingPosition() {
        if (!("geolocation" in navigator)) {
            showError(trackingError, "This browser does not support location tracking.");
            return;
        }
        watchId = navigator.geolocation.watchPosition(
            (position) => {
                logPoint(position.coords.latitude, position.coords.longitude);
            },
            (err) => {
                showError(trackingError, `Location error: ${err.message}`);
            },
            { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
        );
    }

    function stopWatchingPosition() {
        if (watchId !== null && "geolocation" in navigator) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }
    }

    async function handleStart() {
        setupError.classList.add("hidden");
        const consent = document.getElementById("location-consent").checked;
        const mode = document.getElementById("transport-mode").value;

        if (!consent) {
            showError(setupError, "Location consent is required to start a journey.");
            return;
        }

        try {
            const data = await api("/api/journeys/start/", {
                method: "POST",
                body: { transport_mode: mode, legal_disclaimer_accepted: true },
            });
            journeyId = data.journey.id;
            document.getElementById("active-mode-label").textContent = data.journey.transport_mode.name;
            setupPanel.classList.add("hidden");
            activePanel.classList.remove("hidden");
            initMap();
            startWatchingPosition();
        } catch (err) {
            showError(setupError, err.message);
        }
    }

    async function handleStop() {
        trackingError.classList.add("hidden");
        stopWatchingPosition();
        try {
            const data = await api(`/api/journeys/${journeyId}/stop/`, { method: "POST" });
            activePanel.classList.add("hidden");
            resultPanel.classList.remove("hidden");
            document.getElementById("result-distance").textContent = `${data.journey.distance_km} km`;
            document.getElementById("result-carbon").textContent = `${data.journey.carbon_saved_g} g CO2`;
            document.getElementById("result-points").textContent = `+${data.journey.points_awarded}`;
            document.getElementById("result-hash").textContent = data.journey.integrity_hash;
            document.getElementById("result-link").href = `/journeys/${data.journey.id}/`;
            const achievements = data.journey.achievements_unlocked || [];
            if (achievements.length > 0) {
                const achievementsEl = document.getElementById("result-achievements");
                achievementsEl.textContent = `Unlocked: ${achievements.join(", ")}`;
                achievementsEl.classList.remove("hidden");
            }
        } catch (err) {
            showError(trackingError, err.message);
            startWatchingPosition(); // stop failed (e.g. <2 points) — resume logging
        }
    }

    document.getElementById("start-btn").addEventListener("click", handleStart);
    document.getElementById("stop-btn").addEventListener("click", handleStop);

    if (journeyId) {
        initMap();
        loadExistingPoints().then(startWatchingPosition);
    }
})();
