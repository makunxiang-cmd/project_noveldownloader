(function () {
  const panel = document.querySelector("[data-event-source]");
  if (!panel || !window.EventSource) {
    return;
  }

  const statusNode = panel.querySelector("[data-job-status]");
  const logNode = panel.querySelector("[data-progress-log]");
  const resultNode = panel.querySelector("[data-job-result]");
  const resultLabel = panel.querySelector("[data-result-label]");
  const resultMessage = panel.querySelector("[data-result-message]");
  const resultOutput = panel.querySelector("[data-result-output]");
  const resultOutputPath = panel.querySelector("[data-result-output-path]");
  const resultLibrary = panel.querySelector("[data-result-library]");
  const resultLibraryLink = panel.querySelector("[data-result-library-link]");
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
    renderResult(data);
    source.close();
  });

  function renderResult(data) {
    if (!resultNode) {
      return;
    }
    resultNode.hidden = false;
    if (data.status === "succeeded") {
      if (resultLabel) resultLabel.textContent = "Succeeded";
      if (resultMessage) resultMessage.textContent = "Download finished.";
      if (resultOutput && resultOutputPath && data.output_path) {
        resultOutputPath.textContent = data.output_path;
        resultOutput.hidden = false;
      }
      if (resultLibrary && resultLibraryLink && data.novel_id != null) {
        resultLibraryLink.textContent = "ID " + data.novel_id;
        resultLibraryLink.href = "/library/" + data.novel_id;
        resultLibrary.hidden = false;
      }
    } else if (data.status === "failed") {
      if (resultLabel) resultLabel.textContent = "Failed";
      if (resultMessage) resultMessage.textContent = data.error || "Download failed.";
    }
  }
})();
