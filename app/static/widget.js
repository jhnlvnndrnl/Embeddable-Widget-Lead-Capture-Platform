(function () {
  "use strict";

  // Prevent multiple executions for the same widget
  if (window.__FLYRANK_WIDGET_INITIALIZED__) {
    return;
  }
  window.__FLYRANK_WIDGET_INITIALIZED__ = true;

  // Locate the current script tag to extract configuration params and API base URL
  var currentScript =
    document.currentScript ||
    (function () {
      var scripts = document.getElementsByTagName("script");
      return scripts[scripts.length - 1];
    })();

  if (!currentScript) {
    console.error("[FlyRank Widget] Unable to locate host script element.");
    return;
  }

  var scriptSrc = currentScript.src;
  var widgetId = null;
  var apiBase = "";

  try {
    var parsedUrl = new URL(scriptSrc);
    apiBase = parsedUrl.origin;
    widgetId =
      parsedUrl.searchParams.get("id") ||
      currentScript.getAttribute("data-widget-id");
  } catch (e) {
    console.error("[FlyRank Widget] Invalid script src URL:", scriptSrc);
    return;
  }

  if (!widgetId) {
    console.error(
      "[FlyRank Widget] Missing widget ID! Add ?id=YOUR_ID to the script src or set data-widget-id."
    );
    return;
  }

  // Fetch widget configuration from public API
  fetch(apiBase + "/widgets/" + encodeURIComponent(widgetId) + "/config")
    .then(function (res) {
      if (!res.ok) {
        throw new Error("Failed to load widget config (Status: " + res.status + ")");
      }
      return res.json();
    })
    .then(function (config) {
      renderWidget(config, apiBase);
    })
    .catch(function (err) {
      console.error("[FlyRank Widget] Error initializing widget:", err);
    });

  function renderWidget(config, baseUrl) {
    var primaryColor = config.primary_color || "#4F46E5";
    var isPopover = config.widget_type === "popover";

    // Inject Widget CSS
    var style = document.createElement("style");
    style.innerHTML = [
      ".fr-widget-card {",
      "  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;",
      "  background: #ffffff;",
      "  color: #1f2937;",
      "  border-radius: 12px;",
      "  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);",
      "  border: 1px solid #e5e7eb;",
      "  padding: 24px;",
      "  max-width: 400px;",
      "  margin: 16px auto;",
      "  box-sizing: border-box;",
      "  position: relative;",
      "  z-index: 9999;",
      "}",
      isPopover
        ? ".fr-widget-popover-container { position: fixed; bottom: 24px; right: 24px; z-index: 99999; }"
        : "",
      ".fr-widget-title { font-size: 20px; font-weight: 700; margin: 0 0 8px 0; color: #111827; }",
      ".fr-widget-desc { font-size: 14px; color: #6b7280; margin: 0 0 16px 0; line-height: 1.4; }",
      ".fr-field-group { margin-bottom: 14px; text-align: left; }",
      ".fr-field-label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px; color: #374151; }",
      ".fr-field-input { width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; box-sizing: border-box; outline: none; transition: border-color 0.2s; }",
      ".fr-field-input:focus { border-color: " + primaryColor + "; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15); }",
      ".fr-submit-btn { width: 100%; background: " + primaryColor + "; color: #ffffff; border: none; padding: 12px; border-radius: 6px; font-size: 15px; font-weight: 600; cursor: pointer; transition: opacity 0.2s; }",
      ".fr-submit-btn:hover { opacity: 0.9; }",
      ".fr-submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }",
      ".fr-msg { margin-top: 12px; font-size: 13px; padding: 8px 12px; border-radius: 6px; text-align: center; }",
      ".fr-msg-success { background: #def7ec; color: #03543f; }",
      ".fr-msg-error { background: #fde8e8; color: #9b1c1c; }",
      ".fr-toggle-btn { background: " + primaryColor + "; color: #fff; width: 56px; height: 56px; border-radius: 50%; border: none; box-shadow: 0 4px 14px rgba(0,0,0,0.25); cursor: pointer; font-size: 24px; display: flex; align-items: center; justify-content: center; margin-left: auto; }"
    ].join("\n");
    document.head.appendChild(style);

    // Build DOM container
    var container = document.createElement("div");
    if (isPopover) {
      container.className = "fr-widget-popover-container";
    }

    var card = document.createElement("div");
    card.className = "fr-widget-card";
    if (isPopover) {
      card.style.display = "none"; // start closed
    }

    // Header
    var titleEl = document.createElement("h3");
    titleEl.className = "fr-widget-title";
    titleEl.innerText = config.title;
    card.appendChild(titleEl);

    var descEl = document.createElement("p");
    descEl.className = "fr-widget-desc";
    descEl.innerText = config.description;
    card.appendChild(descEl);

    // Form
    var form = document.createElement("form");
    form.id = "fr-form-" + config.id;

    // Anti-Spam Honeypot Field (Hidden from humans)
    var hpInput = document.createElement("input");
    hpInput.type = "text";
    hpInput.name = "_hp_trap";
    hpInput.style.display = "none";
    hpInput.tabIndex = -1;
    hpInput.autocomplete = "off";
    form.appendChild(hpInput);

    // Dynamic Fields
    (config.fields_schema || []).forEach(function (field) {
      var group = document.createElement("div");
      group.className = "fr-field-group";

      var label = document.createElement("label");
      label.className = "fr-field-label";
      label.innerText = field.label + (field.required ? " *" : "");
      group.appendChild(label);

      var input;
      if (field.type === "textarea") {
        input = document.createElement("textarea");
        input.rows = 3;
      } else {
        input = document.createElement("input");
        input.type = field.type || "text";
      }

      input.name = field.name;
      input.className = "fr-field-input";
      if (field.required) {
        input.required = true;
      }
      group.appendChild(input);
      form.appendChild(group);
    });

    // Submit Button
    var submitBtn = document.createElement("button");
    submitBtn.type = "submit";
    submitBtn.className = "fr-submit-btn";
    submitBtn.innerText = config.button_text || "Submit";
    form.appendChild(submitBtn);

    // Status Message Box
    var msgBox = document.createElement("div");
    msgBox.className = "fr-msg";
    msgBox.style.display = "none";
    form.appendChild(msgBox);

    // Handle Form Submit
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      submitBtn.disabled = true;
      submitBtn.innerText = "Submitting...";
      msgBox.style.display = "none";

      var formData = new FormData(form);
      var payloadData = {};
      var hpValue = formData.get("_hp_trap") || null;

      formData.forEach(function (value, key) {
        if (key !== "_hp_trap") {
          payloadData[key] = value;
        }
      });

      var submissionPayload = {
        widget_id: config.id,
        data: payloadData,
        _hp_trap: hpValue ? String(hpValue) : null
      };

      fetch(baseUrl + "/submissions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify(submissionPayload)
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, status: res.status, data: data };
          });
        })
        .then(function (result) {
          submitBtn.disabled = false;
          submitBtn.innerText = config.button_text || "Submit";

          if (result.ok) {
            msgBox.className = "fr-msg fr-msg-success";
            msgBox.innerText = result.data.message || "Thank you! We received your submission.";
            msgBox.style.display = "block";
            form.reset();
          } else {
            msgBox.className = "fr-msg fr-msg-error";
            msgBox.innerText = result.data.detail || "Submission failed. Please try again.";
            msgBox.style.display = "block";
          }
        })
        .catch(function (err) {
          submitBtn.disabled = false;
          submitBtn.innerText = config.button_text || "Submit";
          msgBox.className = "fr-msg fr-msg-error";
          msgBox.innerText = "Network error. Please check your connection.";
          msgBox.style.display = "block";
        });
    });

    card.appendChild(form);
    container.appendChild(card);

    if (isPopover) {
      var toggleBtn = document.createElement("button");
      toggleBtn.className = "fr-toggle-btn";
      toggleBtn.innerHTML = "💬";
      toggleBtn.onclick = function () {
        if (card.style.display === "none") {
          card.style.display = "block";
          toggleBtn.innerHTML = "✕";
        } else {
          card.style.display = "none";
          toggleBtn.innerHTML = "💬";
        }
      };
      container.appendChild(toggleBtn);
    }

    // Append to target container if exists (#flyrank-widget-container), otherwise body
    var target = document.getElementById("flyrank-widget-container");
    if (target && !isPopover) {
      target.appendChild(container);
    } else {
      document.body.appendChild(container);
    }
  }
})();
