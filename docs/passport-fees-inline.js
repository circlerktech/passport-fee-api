/**
 * Passport Fee Inline Updater
 * Fills in fee values into existing HTML elements using data attributes.
 * Works with any table builder (WordPress, hand-coded, etc.)
 *
 * Usage: Add data-fee attributes to any element where a fee should appear.
 * Then include this script on the page:
 *   <script src="https://circlerktech.github.io/passport-fee-api/passport-fees-inline.js"></script>
 *
 * All available spans (copy-paste ready):
 *
 * Application Fees:
 *   <span data-fee="application.adult_book"></span>            → $130.00
 *   <span data-fee="application.child_book"></span>            → $100.00
 *   <span data-fee="application.adult_card"></span>            → $30.00
 *   <span data-fee="application.child_card"></span>            → $15.00
 *   <span data-fee="application.adult_book_card"></span>       → $160.00
 *   <span data-fee="application.child_book_card"></span>       → $115.00
 *
 * Execution & Photo Fees:
 *   <span data-fee="execution.execution_fee"></span>           → $35.00
 *   <span data-fee="execution.photo"></span>                   → $10.00
 *
 * Shipping Fees:
 *   <span data-fee="shipping.priority_express"></span>         → $33.25
 *   <span data-fee="shipping.return_delivery"></span>         → $22.05
 *   <span data-fee="shipping.expedite"></span>                 → $60.00
 *
 * Delivery Times:
 *   <span data-fee="shipping.priority_express.delivery_time"></span>   → 1-2 Days
 *   <span data-fee="shipping.return_delivery.delivery_time"></span>   → 1-3 Days
 */
(function () {
  "use strict";

  // Auto-detect base URL from the script's own location
  var scripts = document.getElementsByTagName("script");
  var currentScript = scripts[scripts.length - 1];
  var baseUrl = currentScript.src.replace(/\/[^/]*$/, "");

  var FEES_URL = baseUrl + "/fees.json";

  function formatAmount(amount) {
    return "$" + Number(amount).toFixed(2);
  }

  function resolvePath(data, path) {
    // path like "application.adult_book" or "shipping.priority_express.delivery_time"
    var parts = path.split(".");
    var section = parts[0];   // "application", "execution", "shipping"
    var itemKey = parts[1];   // "adult_book", "priority_express", etc.
    var field = parts[2];     // optional: "delivery_time"

    var fees = data.fees || {};
    if (!fees[section] || !fees[section].items || !fees[section].items[itemKey]) {
      return null;
    }

    var item = fees[section].items[itemKey];

    if (field === "delivery_time") {
      return item.delivery_time || null;
    }

    return formatAmount(item.amount);
  }

  function fillFees(data) {
    var elements = document.querySelectorAll("[data-fee]");
    for (var i = 0; i < elements.length; i++) {
      var el = elements[i];
      var path = el.getAttribute("data-fee");
      var value = resolvePath(data, path);
      if (value !== null) {
        el.textContent = value;
      }
    }
  }

  function load() {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", FEES_URL, true);
    xhr.onload = function () {
      if (xhr.status === 200) {
        try {
          fillFees(JSON.parse(xhr.responseText));
        } catch (e) {
          console.error("Passport fees: error parsing data", e);
        }
      }
    };
    xhr.onerror = function () {
      console.error("Passport fees: unable to load fee data");
    };
    xhr.send();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
})();
