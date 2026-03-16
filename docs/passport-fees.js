/**
 * Passport Fee Table Widget
 * Fetches fees.json from this GitHub Pages site and renders
 * a styled fee table matching the Benton County format.
 *
 * Usage: <div id="passport-fees"></div>
 *        <script src="https://<your-gh-pages>/passport-fees.js"></script>
 *
 * Optional attributes on the div:
 *   data-show-pdf="true"     - Show a download PDF link
 *   data-show-updated="true" - Show "last updated" date
 */
(function () {
  "use strict";

  // Base URL — auto-detect from the script's own location
  var scripts = document.getElementsByTagName("script");
  var currentScript = scripts[scripts.length - 1];
  var baseUrl = currentScript.src.replace(/\/[^/]*$/, "");

  var FEES_URL = baseUrl + "/fees.json";
  var PDF_URL = baseUrl + "/Fee-Schedule.pdf";

  var container = document.getElementById("passport-fees");
  if (!container) return;

  var showPdf = container.getAttribute("data-show-pdf") === "true";
  var showUpdated = container.getAttribute("data-show-updated") === "true";

  function formatAmount(amount) {
    return "$" + Number(amount).toFixed(2);
  }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        if (key === "textContent") {
          node.textContent = attrs[key];
        } else if (key === "innerHTML") {
          node.innerHTML = attrs[key];
        } else if (key === "className") {
          node.className = attrs[key];
        } else {
          node.setAttribute(key, attrs[key]);
        }
      });
    }
    if (children) {
      children.forEach(function (child) {
        if (typeof child === "string") {
          node.appendChild(document.createTextNode(child));
        } else if (child) {
          node.appendChild(child);
        }
      });
    }
    return node;
  }

  function addStyles() {
    var css = [
      ".pf-table { width: 100%; border-collapse: collapse; margin-bottom: 16px; font-family: inherit; font-size: 14px; }",
      ".pf-table th, .pf-table td { padding: 8px 12px; border: 1px solid #ccc; }",
      ".pf-table th { background-color: #4F81BD; color: #fff; text-align: left; font-weight: bold; }",
      ".pf-table th.pf-fee-col { text-align: right; width: 120px; }",
      ".pf-table td { vertical-align: top; }",
      ".pf-table td.pf-fee { text-align: right; white-space: nowrap; font-weight: 500; }",
      ".pf-table tr:nth-child(even) { background-color: #f9f9f9; }",
      ".pf-note { font-size: 12px; color: #666; margin-top: 4px; }",
      ".pf-pdf-link { display: inline-block; margin: 12px 0; padding: 8px 16px; background: #4F81BD; color: #fff; text-decoration: none; border-radius: 4px; }",
      ".pf-pdf-link:hover { background: #3a6a9e; }",
      ".pf-updated { font-size: 12px; color: #888; margin-top: 8px; }",
      ".pf-error { color: #c00; padding: 12px; border: 1px solid #c00; border-radius: 4px; }",
    ].join("\n");

    var style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
  }

  function buildSection(headerText, rows) {
    var table = el("table", { className: "pf-table" });
    var thead = el("thead", null, [
      el("tr", null, [
        el("th", { textContent: headerText }),
        el("th", { textContent: "Fee", className: "pf-fee-col" }),
      ]),
    ]);
    table.appendChild(thead);

    var tbody = el("tbody");
    rows.forEach(function (row) {
      var descCell = el("td");
      descCell.textContent = row.label;
      if (row.note) {
        descCell.appendChild(el("div", { textContent: row.note, className: "pf-note" }));
      }
      var feeCell = el("td", { textContent: row.fee, className: "pf-fee" });
      tbody.appendChild(el("tr", null, [descCell, feeCell]));
    });
    table.appendChild(tbody);
    return table;
  }

  function render(data) {
    container.innerHTML = "";

    var fees = data.fees;
    var deliveryTimes = data.delivery_times || {};
    var expressTime = (deliveryTimes.usps_priority_express || {}).timeframe || "1-2 Days";

    // Adult fees
    var adultRows = [];
    var app = fees.application.items;
    adultRows.push({ label: "Adult Passport Book", fee: formatAmount(app.adult_book.amount) });
    adultRows.push({
      label: "Adult Passport Card",
      note: "Not valid for international air travel. Valid only for land/sea travel to Canada, Mexico, Bermuda, and the Caribbean.",
      fee: formatAmount(app.adult_card.amount),
    });
    adultRows.push({ label: "Adult Passport Book & Card", fee: formatAmount(app.adult_book_card.amount) });
    container.appendChild(buildSection("ADULT APPLICANTS (Age 16 Years or Older)", adultRows));

    // Minor fees
    var minorRows = [];
    minorRows.push({ label: "Minor Passport Book", fee: formatAmount(app.child_book.amount) });
    minorRows.push({
      label: "Minor Passport Card",
      note: "Not valid for international air travel. Valid only for land/sea travel to Canada, Mexico, Bermuda, and the Caribbean.",
      fee: formatAmount(app.child_card.amount),
    });
    minorRows.push({ label: "Minor Passport Book & Card", fee: formatAmount(app.child_book_card.amount) });
    container.appendChild(buildSection("ALL MINOR APPLICANTS (Under the Age of 16)", minorRows));

    // Additional fees
    var addlRows = [];
    var exe = fees.execution.items;
    var ship = fees.shipping.items;

    addlRows.push({
      label: "Execution Fee per applicant Adult & Minor",
      note: "Payable to Benton County Circuit Clerk's Office",
      fee: formatAmount(exe.execution_fee.amount),
    });
    addlRows.push({ label: "Passport Photos", fee: formatAmount(exe.photo.amount) });
    addlRows.push({
      label: "Priority Mail Express - Overnight up to " + expressTime + " Guarantee",
      note: "US Mail Service not guaranteed by the Circuit Clerk's Office. Payable to USPS. *USPS rates may change*",
      fee: formatAmount(ship.priority_express.amount),
    });
    addlRows.push({
      label: (ship.return_delivery.delivery_time || "1-3 Days") + " Return Services",
      note: "US Postal Priority Mail Overnight up to " + expressTime + " Guarantee service. (USPS Express Mail\u00ae Service)",
      fee: formatAmount(ship.return_delivery.amount),
    });
    addlRows.push({
      label: "Expedite Fee",
      note: "Payable to the U.S. Department of State",
      fee: formatAmount(ship.expedite.amount),
    });
    container.appendChild(buildSection("Additional Fees", addlRows));

    // PDF download link
    if (showPdf) {
      container.appendChild(
        el("a", { href: PDF_URL, className: "pf-pdf-link", target: "_blank", download: "" }, [
          "Download Fee Schedule (PDF)",
        ])
      );
    }

    // Last updated
    if (showUpdated && data.last_updated) {
      container.appendChild(
        el("div", { className: "pf-updated", textContent: "Fees last verified: " + data.last_updated })
      );
    }
  }

  function loadFees() {
    addStyles();
    container.textContent = "Loading fee schedule...";

    var xhr = new XMLHttpRequest();
    xhr.open("GET", FEES_URL, true);
    xhr.onload = function () {
      if (xhr.status === 200) {
        try {
          var data = JSON.parse(xhr.responseText);
          render(data);
        } catch (e) {
          container.innerHTML = '<div class="pf-error">Error parsing fee data.</div>';
        }
      } else {
        container.innerHTML = '<div class="pf-error">Unable to load current fees. Please try again later.</div>';
      }
    };
    xhr.onerror = function () {
      container.innerHTML = '<div class="pf-error">Unable to load current fees. Please try again later.</div>';
    };
    xhr.send();
  }

  // Load when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadFees);
  } else {
    loadFees();
  }
})();
