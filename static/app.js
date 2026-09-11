/**
 * Hiver AI Customer Support Agent - Frontend Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  const tweetInput = document.getElementById("tweet-input");
  const brandSelect = document.getElementById("brand-select");
  const inputCharCount = document.getElementById("input-char-count");
  const processBtn = document.getElementById("process-btn");
  const btnSpinner = document.getElementById("btn-spinner");
  const resultsSection = document.getElementById("results-section");
  const presetContainer = document.getElementById("preset-container");

  // Presets mapping with diverse real-world edge cases
  const PRESETS = {
    delayed_package: {
      brand: "AmazonHelp",
      tweet: "@AmazonHelp My package was supposed to arrive yesterday by 8 PM, tracking says 'Out for Delivery' since 9 AM yesterday. Where is order #402-8921821-291?"
    },
    billing_charge: {
      brand: "AmazonHelp",
      tweet: "@AmazonHelp I was charged $14.99 twice for Prime membership this morning on my card! Please reverse the duplicate charge."
    },
    app_crash: {
      brand: "AppleSupport",
      tweet: "@AppleSupport My iPhone 15 keeps crashing to the black Apple logo screen every time I open the Camera app on iOS 18.0.1. Already restarted twice."
    },
    account_hacked: {
      brand: "AmazonHelp",
      tweet: "@AmazonHelp I think someone hacked my Amazon account! I received an email about an order placed for $800 to an address in another state. HELP!"
    },
    return_faq: {
      brand: "NikeSupport",
      tweet: "@NikeSupport What is your holiday return policy for shoes purchased in November? Can they be returned in January?"
    },
    legal_escalation: {
      brand: "British_Airways",
      tweet: "@British_Airways You lost our luggage 6 days ago with life-saving medication inside! Agents at Heathrow are completely ignoring us. This is criminal neglect. We are contacting our attorney to sue you!"
    },
    accidental_pii: {
      brand: "AmazonHelp",
      tweet: "@AmazonHelp please refund my card 4532-8821-9921-3321 immediately and email john.doe@example.com, this is ridiculous!"
    }
  };

  // 1. Initialize stats & health check
  fetchHealthAndStats();

  // 2. Character counter
  tweetInput.addEventListener("input", () => {
    const len = tweetInput.value.length;
    inputCharCount.textContent = `${len} / 280`;
    if (len > 280) {
      inputCharCount.style.color = "var(--accent-rose)";
    } else {
      inputCharCount.style.color = "var(--text-muted)";
    }
  });

  // 3. Preset chips handler
  presetContainer.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;

    document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");

    const scenarioKey = chip.getAttribute("data-scenario");
    const scenario = PRESETS[scenarioKey];
    if (scenario) {
      tweetInput.value = scenario.tweet;
      brandSelect.value = scenario.brand;
      tweetInput.dispatchEvent(new Event("input"));
      // Automatically trigger processing for instant demo experience
      runPipeline();
    }
  });

  // 4. Process button click
  processBtn.addEventListener("click", () => {
    runPipeline();
  });

  // Toggle exemplars accordion
  const toggleExemplars = document.getElementById("toggle-exemplars");
  const exemplarsList = document.getElementById("exemplars-list");
  toggleExemplars.addEventListener("click", () => {
    if (exemplarsList.style.display === "none") {
      exemplarsList.style.display = "flex";
      toggleExemplars.querySelector(".toggle-icon").textContent = "▼";
    } else {
      exemplarsList.style.display = "none";
      toggleExemplars.querySelector(".toggle-icon").textContent = "▶";
    }
  });

  async function fetchHealthAndStats() {
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        document.getElementById("total-exemplars").textContent = data.indexed_exemplars || "23";
        const statusEl = document.getElementById("system-status");
        statusEl.textContent = data.gemini_active ? "Gemini LLM Active" : "Deterministic Mode (Fast)";
      }
    } catch (e) {
      console.warn("Could not fetch health status:", e);
    }
  }

  async function runPipeline() {
    const text = tweetInput.value.trim();
    if (!text) {
      alert("Please enter a customer tweet or select a test scenario.");
      return;
    }

    // Set loading state
    processBtn.disabled = true;
    btnSpinner.style.display = "inline-block";
    processBtn.querySelector(".btn-text").textContent = "Analyzing Tweet...";

    try {
      const payload = {
        tweet_text: text,
        brand_context: brandSelect.value,
        author_id: "customer_user"
      };

      const response = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data = await response.json();
      renderPipelineResults(data);
    } catch (err) {
      console.error(err);
      alert("Error running pipeline: " + err.message);
    } finally {
      processBtn.disabled = false;
      btnSpinner.style.display = "none";
      processBtn.querySelector(".btn-text").textContent = "Execute AI Pipeline";
    }
  }

  function renderPipelineResults(data) {
    resultsSection.style.display = "flex";
    resultsSection.scrollIntoView({ behavior: "smooth", block: "nearest" });

    // Execution time
    document.getElementById("execution-time").textContent = `⏱️ ${data.execution_time_ms} ms`;

    // Task 1: Intent
    const intent = data.intent_classification;
    document.getElementById("res-primary-intent").textContent = intent.primary_intent;
    document.getElementById("res-intent-confidence").textContent = `${Math.round(intent.confidence * 100)}% Confidence`;

    const sentimentEl = document.getElementById("res-sentiment");
    sentimentEl.textContent = intent.sentiment;
    sentimentEl.className = `sentiment-indicator sentiment-${intent.sentiment}`;

    const urgencyEl = document.getElementById("res-urgency");
    urgencyEl.textContent = intent.urgency;
    urgencyEl.className = `urgency-indicator urgency-${intent.urgency}`;

    document.getElementById("res-intent-reasoning").textContent = intent.reasoning;

    // Entities
    const entitiesContainer = document.getElementById("entities-container");
    const entitiesList = document.getElementById("res-entities");
    entitiesList.innerHTML = "";
    if (intent.extracted_entities && Object.keys(intent.extracted_entities).length > 0) {
      entitiesContainer.style.display = "block";
      for (const [key, val] of Object.entries(intent.extracted_entities)) {
        const pill = document.createElement("span");
        pill.className = "entity-pill";
        pill.textContent = `${key}: ${val}`;
        entitiesList.appendChild(pill);
      }
    } else {
      entitiesContainer.style.display = "none";
    }

    // Task 2: Grounded Response
    const grounded = data.grounded_response;
    const brand = data.preprocessed.handles_detected[0] ? data.preprocessed.handles_detected[0].replace("@", "") : brandSelect.value;
    document.getElementById("res-brand-avatar").textContent = brand.charAt(0).toUpperCase();
    document.getElementById("res-brand-name").textContent = brand;
    document.getElementById("res-brand-handle").textContent = `@${brand}`;
    document.getElementById("res-reply-text").textContent = grounded.generated_reply;
    document.getElementById("res-reply-length").textContent = `${grounded.character_count} / 280 chars`;

    const dmBadge = document.getElementById("res-reply-dm");
    if (grounded.direct_message_suggested) {
      dmBadge.style.display = "inline-block";
      dmBadge.textContent = "✉️ DM Channel Suggested";
    } else {
      dmBadge.style.display = "none";
    }

    document.getElementById("res-reply-tone").textContent = grounded.tone;

    // Grounding Exemplars
    const exemplars = grounded.grounded_in_exemplars || [];
    document.getElementById("exemplar-count").textContent = exemplars.length;
    const exemplarsList = document.getElementById("exemplars-list");
    exemplarsList.innerHTML = "";

    exemplars.forEach((ex, idx) => {
      const item = document.createElement("div");
      item.className = "exemplar-item";
      const sim = ex.similarity_score ? `${Math.round(ex.similarity_score * 100)}% Match` : "Historical Precedent";
      item.innerHTML = `
        <div class="exemplar-top">
          <span>#${idx + 1} • @${ex.brand} [${ex.intent}]</span>
          <span>${sim}</span>
        </div>
        <div class="exemplar-query">"${escapeHtml(ex.customer_query)}"</div>
        <div class="exemplar-response"><strong>Resolved:</strong> "${escapeHtml(ex.brand_response)}"</div>
      `;
      exemplarsList.appendChild(item);
    });

    // Task 3: Automation Decision
    const auto = data.automation_decision;
    const decisionBadge = document.getElementById("res-decision-badge");
    decisionBadge.textContent = auto.decision === "AUTOMATE" ? "✓ AUTOMATE" : "⚠️ ESCALATE TO HUMAN";
    decisionBadge.className = `decision-badge decision-${auto.decision}`;

    document.getElementById("res-decision-confidence").textContent = `${Math.round(auto.confidence * 100)}% Safety Confidence`;
    document.getElementById("res-routing-team").textContent = auto.routing_team;
    document.getElementById("res-decision-reasoning").textContent = auto.reasoning;

    const riskContainer = document.getElementById("risk-factors-container");
    const riskList = document.getElementById("res-risk-factors");
    riskList.innerHTML = "";
    if (auto.risk_factors && auto.risk_factors.length > 0) {
      riskContainer.style.display = "block";
      auto.risk_factors.forEach((rf) => {
        const li = document.createElement("li");
        li.textContent = rf;
        riskList.appendChild(li);
      });
    } else {
      riskContainer.style.display = "none";
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
