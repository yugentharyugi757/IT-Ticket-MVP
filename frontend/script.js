function showApiError(response, fallbackMessage) {
  return response
    .json()
    .catch(() => null)
    .then((errorData) => {
      const detail = errorData?.detail;
      throw new Error(
        typeof detail === "string"
          ? detail
          : `${fallbackMessage} (HTTP ${response.status}).`,
      );
    });
}

function initializeTicketForm() {
  const ticketForm = document.querySelector("#ticket-form");
  if (!ticketForm) {
    return;
  }

  const submitButton = document.querySelector("#submit-button");
  const loadingIndicator = document.querySelector("#loading-indicator");
  const formError = document.querySelector("#form-error");
  const resultSection = document.querySelector("#result-section");

  ticketForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    formError.textContent = "";
    resultSection.hidden = true;

    const formData = new FormData(ticketForm);
    const name = String(formData.get("name") ?? "").trim();
    const description = String(formData.get("description") ?? "").trim();
    if (!name || !description) {
      formError.textContent = "Please enter your name and describe your IT issue.";
      formError.hidden = false;
      return;
    }

    submitButton.disabled = true;
    loadingIndicator.hidden = false;

    try {
      const response = await fetch("/api/tickets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description }),
      });

      if (!response.ok) {
        await showApiError(response, "We couldn’t submit your ticket");
      }

      const ticket = await response.json();
      document.querySelector("#result-ticket-id").textContent = `#${ticket.id}`;
      const priority = document.querySelector("#result-priority");
      const priorityName = String(ticket.priority);
      const priorityClass = ["high", "medium", "low"].includes(
        priorityName.toLowerCase(),
      )
        ? priorityName.toLowerCase()
        : "unknown";
      priority.textContent = priorityName;
      priority.className = `priority-badge priority-${priorityClass}`;
      document.querySelector("#result-confidence").textContent =
        `${(Number(ticket.confidence) * 100).toFixed(1)}%`;

      const submittedAt = new Date(ticket.created_at);
      document.querySelector("#result-time").textContent = Number.isNaN(
        submittedAt.getTime(),
      )
        ? ticket.created_at
        : submittedAt.toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
          });

      resultSection.hidden = false;
      ticketForm.reset();
      resultSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) {
      formError.textContent =
        error instanceof Error
          ? error.message
          : "A network error occurred. Please try again.";
      formError.hidden = false;
    } finally {
      submitButton.disabled = false;
      loadingIndicator.hidden = true;
    }
  });
}

function initializeAdminDashboard() {
  const refreshButton = document.querySelector("#refresh-button");
  if (!refreshButton) {
    return;
  }

  const message = document.querySelector("#admin-message");
  const ticketCount = document.querySelector("#ticket-count");
  const tableWrap = document.querySelector("#ticket-table-wrap");
  const ticketRows = document.querySelector("#ticket-rows");
  const emptyState = document.querySelector("#empty-state");

  let openTickets = [];
  const clearedTicketIds = new Set();

  function renderTickets() {
    ticketRows.replaceChildren();
    ticketCount.textContent = `${openTickets.length} open ${
      openTickets.length === 1 ? "ticket" : "tickets"
    }`;
    tableWrap.hidden = openTickets.length === 0;
    emptyState.hidden = openTickets.length !== 0;

    for (const ticket of openTickets) {
      const row = document.createElement("tr");
      const ticketCell = document.createElement("td");
      const raisedCell = document.createElement("td");
      const actionCell = document.createElement("td");
      const description = document.createElement("span");
      const ticketMeta = document.createElement("span");
      const ticketReference = document.createElement("span");
      const priority = document.createElement("span");
      const raisedTime = document.createElement("time");
      const clearButton = document.createElement("button");

      description.className = "ticket-description";
      description.textContent = ticket.description;

      ticketMeta.className = "ticket-meta";
      ticketReference.textContent = `#${ticket.id} · ${ticket.name}`;

      const priorityName = String(ticket.priority);
      const priorityClass = ["high", "medium", "low"].includes(
        priorityName.toLowerCase(),
      )
        ? priorityName.toLowerCase()
        : "unknown";
      priority.className = `priority-badge priority-${priorityClass}`;
      priority.textContent = priorityName;

      ticketMeta.append(ticketReference, priority);
      ticketCell.append(description, ticketMeta);

      const raisedDate = new Date(ticket.created_at);
      raisedTime.className = "raised-time";
      raisedTime.dateTime = ticket.created_at;
      raisedTime.textContent = Number.isNaN(raisedDate.getTime())
        ? ticket.created_at
        : raisedDate.toLocaleTimeString(undefined, {
            hour: "numeric",
            minute: "2-digit",
          });
      raisedCell.append(raisedTime);

      clearButton.className = "clear-button";
      clearButton.type = "button";
      clearButton.textContent = "CLEAR";
      clearButton.setAttribute("aria-label", `Clear ticket ${ticket.id}`);
      clearButton.addEventListener("click", () =>
        clearTicket(ticket.id, clearButton),
      );
      actionCell.append(clearButton);

      row.append(ticketCell, raisedCell, actionCell);
      ticketRows.append(row);
    }
  }

  async function loadTickets() {
    refreshButton.disabled = true;
    message.hidden = true;
    message.textContent = "";

    try {
      const response = await fetch("/api/tickets");
      if (!response.ok) {
        await showApiError(response, "Could not load tickets");
      }

      const tickets = await response.json();
      if (!Array.isArray(tickets)) {
        throw new Error("The server returned an invalid ticket list.");
      }

      openTickets = tickets
        .filter((ticket) => !clearedTicketIds.has(ticket.id))
        .sort((first, second) => {
          const firstTime = Date.parse(first.created_at);
          const secondTime = Date.parse(second.created_at);
          if (Number.isFinite(firstTime) && Number.isFinite(secondTime)) {
            return secondTime - firstTime;
          }
          return second.id - first.id;
        });
      renderTickets();
    } catch (error) {
      message.textContent =
        error instanceof Error
          ? error.message
          : "A network error occurred while loading tickets.";
      message.hidden = false;
    } finally {
      refreshButton.disabled = false;
    }
  }

  async function clearTicket(ticketId, button) {
    button.disabled = true;
    message.hidden = true;
    message.textContent = "";

    try {
      const response = await fetch(
        `/api/tickets/${encodeURIComponent(ticketId)}`,
        { method: "DELETE" },
      );
      if (!response.ok) {
        await showApiError(response, "Could not clear ticket");
      }

      clearedTicketIds.add(ticketId);
      openTickets = openTickets.filter((ticket) => ticket.id !== ticketId);
      renderTickets();
    } catch (error) {
      button.disabled = false;
      message.textContent =
        error instanceof Error
          ? error.message
          : "A network error occurred while clearing the ticket.";
      message.hidden = false;
    }
  }

  refreshButton.addEventListener("click", loadTickets);
  loadTickets();
}

initializeTicketForm();
initializeAdminDashboard();
