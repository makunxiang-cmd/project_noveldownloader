(function () {
  const panel = document.querySelector("[data-event-source]");
  if (!panel || !window.EventSource) {
    return;
  }

  const statusNode = panel.querySelector("[data-job-status]");
  const logNode = panel.querySelector("[data-progress-log]");
  const source = new EventSource(panel.dataset.eventSource);

  source.addEventListener("progress", function (event) {
    if (!logNode) {
      return;
    }
    const data = JSON.parse(event.data);
    const item = document.createElement("li");
    item.textContent = data.message || data.stage || data.kind;
    logNode.appendChild(item);
  });

  source.addEventListener("status", function (event) {
    const data = JSON.parse(event.data);
    if (statusNode) {
      statusNode.textContent = data.status;
    }
    source.close();
  });
})();
