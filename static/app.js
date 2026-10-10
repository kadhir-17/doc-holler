document.addEventListener("DOMContentLoaded", () => {
  const documentListEl = document.getElementById("document-list");
  const documentCountBadge = document.getElementById("document-count-badge");
  const noDocsWarning = document.getElementById("no-docs-warning");
  const emptyStateEl = document.getElementById("chat-empty-state");
  const messagesContainerEl = document.getElementById("chat-messages");
  const chatFormEl = document.getElementById("chat-form");
  const questionInputEl = document.getElementById("question-input");
  const sendButtonEl = document.getElementById("send-button");
  const fileInputEl = document.getElementById("file-input");
  const uploadDropzoneEl = document.getElementById("upload-dropzone");
  const uploadStatusEl = document.getElementById("upload-status");
  const clearChatBtn = document.getElementById("clear-chat-btn");

  let indexedDocuments = [];
  let isSubmitting = false;

  async function fetchDocuments() {
    try {
      const response = await fetch("/api/v1/documents");
      if (!response.ok) {
        throw new Error(`Failed to load documents: ${response.status}`);
      }
      const data = await response.json();
      indexedDocuments = data.documents || [];
      renderDocumentList();
      updateChatState();
    } catch (err) {
      showUploadStatus(err.message, "error");
    }
  }

  function updateChatState() {
    const hasDocs = indexedDocuments.length > 0;
    if (noDocsWarning) {
      if (hasDocs) {
        noDocsWarning.classList.add("hidden");
      } else {
        noDocsWarning.classList.remove("hidden");
      }
    }
    if (questionInputEl) {
      questionInputEl.disabled = !hasDocs || isSubmitting;
      if (!hasDocs) {
        questionInputEl.placeholder = "Upload documents to enable asking questions...";
      } else {
        questionInputEl.placeholder = "Ask a question across uploaded documents (Enter to send)...";
      }
    }
    if (sendButtonEl) {
      sendButtonEl.disabled = !hasDocs || isSubmitting;
    }
    if (documentCountBadge) {
      documentCountBadge.textContent = String(indexedDocuments.length);
    }
  }

  function renderDocumentList() {
    if (!documentListEl) return;
    documentListEl.innerHTML = "";

    if (indexedDocuments.length === 0) {
      const emptyLi = document.createElement("li");
      emptyLi.className = "py-4 px-3 text-center text-xs text-muted-foreground-1";
      emptyLi.textContent = "No documents indexed. Upload PDF, TXT, or DOCX files.";
      documentListEl.appendChild(emptyLi);
      return;
    }

    indexedDocuments.forEach((doc) => {
      const li = document.createElement("li");
      li.className = "group relative flex items-center justify-between gap-x-2 py-2 px-2.5 rounded-lg hover:bg-muted-hover text-sm";

      const leftDiv = document.createElement("div");
      leftDiv.className = "flex items-center gap-x-2.5 min-w-0";

      const iconSpan = document.createElement("span");
      iconSpan.className = "shrink-0 flex justify-center items-center size-7 rounded-md bg-surface text-primary";
      const iconSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      iconSvg.setAttribute("class", "size-4");
      iconSvg.setAttribute("viewBox", "0 0 24 24");
      iconSvg.setAttribute("fill", "none");
      iconSvg.setAttribute("stroke", "currentColor");
      iconSvg.setAttribute("stroke-width", "2");
      iconSvg.setAttribute("stroke-linecap", "round");
      iconSvg.setAttribute("stroke-linejoin", "round");
      const path1 = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path1.setAttribute("d", "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z");
      const path2 = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      path2.setAttribute("points", "14 2 14 8 20 8");
      iconSvg.appendChild(path1);
      iconSvg.appendChild(path2);
      iconSpan.appendChild(iconSvg);
      leftDiv.appendChild(iconSpan);

      const infoDiv = document.createElement("div");
      infoDiv.className = "truncate";

      const nameP = document.createElement("p");
      nameP.className = "text-xs font-medium text-foreground truncate";
      nameP.textContent = doc.filename;

      const metaP = document.createElement("p");
      metaP.className = "text-[11px] text-muted-foreground-1";
      metaP.textContent = `${doc.chunk_count} chunks • ${formatFileSize(doc.size_bytes)}`;

      infoDiv.appendChild(nameP);
      infoDiv.appendChild(metaP);
      leftDiv.appendChild(infoDiv);

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "shrink-0 flex justify-center items-center size-7 rounded-md text-muted-foreground-1 hover:text-destructive hover:bg-destructive-hover/10 focus:outline-hidden";
      deleteBtn.setAttribute("aria-label", `Delete ${doc.filename}`);

      const trashSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      trashSvg.setAttribute("class", "size-3.5");
      trashSvg.setAttribute("viewBox", "0 0 24 24");
      trashSvg.setAttribute("fill", "none");
      trashSvg.setAttribute("stroke", "currentColor");
      trashSvg.setAttribute("stroke-width", "2");
      trashSvg.setAttribute("stroke-linecap", "round");
      trashSvg.setAttribute("stroke-linejoin", "round");
      const tPath1 = document.createElementNS("http://www.w3.org/2000/svg", "path");
      tPath1.setAttribute("d", "M3 6h18");
      const tPath2 = document.createElementNS("http://www.w3.org/2000/svg", "path");
      tPath2.setAttribute("d", "M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6");
      const tPath3 = document.createElementNS("http://www.w3.org/2000/svg", "path");
      tPath3.setAttribute("d", "M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2");
      trashSvg.appendChild(tPath1);
      trashSvg.appendChild(tPath2);
      trashSvg.appendChild(tPath3);
      deleteBtn.appendChild(trashSvg);

      deleteBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        await deleteDocument(doc.id, doc.filename);
      });

      li.appendChild(leftDiv);
      li.appendChild(deleteBtn);
      documentListEl.appendChild(li);
    });
  }

  function formatFileSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  async function deleteDocument(docId, filename) {
    try {
      const response = await fetch(`/api/v1/documents/${encodeURIComponent(docId)}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to delete document");
      }
      showUploadStatus(`Deleted ${filename}`, "success");
      await fetchDocuments();
    } catch (err) {
      showUploadStatus(err.message, "error");
    }
  }

  async function handleFileUpload(files) {
    if (!files || files.length === 0) return;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    showUploadStatus(`Ingesting ${files.length} document(s)...`, "loading");

    try {
      const response = await fetch("/api/v1/documents", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      const count = data.documents ? data.documents.length : 0;
      let msg = `Successfully indexed ${count} document(s).`;
      if (data.failed && data.failed.length > 0) {
        msg += ` (${data.failed.length} failed)`;
      }
      showUploadStatus(msg, "success");
      await fetchDocuments();
    } catch (err) {
      showUploadStatus(err.message, "error");
    } finally {
      if (fileInputEl) fileInputEl.value = "";
    }
  }

  function showUploadStatus(message, type) {
    if (!uploadStatusEl) return;
    uploadStatusEl.textContent = message;
    uploadStatusEl.className = "text-xs py-1 px-2 rounded-md transition-all";

    if (type === "error") {
      uploadStatusEl.classList.add("text-destructive", "bg-destructive/10");
    } else if (type === "success") {
      uploadStatusEl.classList.add("text-emerald-500", "bg-emerald-500/10");
    } else {
      uploadStatusEl.classList.add("text-primary", "bg-primary/10");
    }

    if (type !== "loading") {
      setTimeout(() => {
        uploadStatusEl.textContent = "";
        uploadStatusEl.className = "hidden";
      }, 5000);
    }
  }

  if (fileInputEl) {
    fileInputEl.addEventListener("change", (e) => {
      handleFileUpload(e.target.files);
    });
  }

  if (uploadDropzoneEl) {
    uploadDropzoneEl.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadDropzoneEl.classList.add("drag-over");
    });
    uploadDropzoneEl.addEventListener("dragleave", () => {
      uploadDropzoneEl.classList.remove("drag-over");
    });
    uploadDropzoneEl.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadDropzoneEl.classList.remove("drag-over");
      if (e.dataTransfer && e.dataTransfer.files) {
        handleFileUpload(e.dataTransfer.files);
      }
    });
  }

  function appendUserMessage(question) {
    if (emptyStateEl) emptyStateEl.classList.add("hidden");

    const messageWrapper = document.createElement("div");
    messageWrapper.className = "py-4 flex flex-col gap-y-1 text-foreground";

    const bubbleRow = document.createElement("div");
    bubbleRow.className = "flex justify-end";

    const bubble = document.createElement("div");
    bubble.className = "text-start bg-surface text-foreground rounded-2xl py-2.5 px-4 max-w-xl text-sm leading-relaxed shadow-xs";
    bubble.textContent = question;

    bubbleRow.appendChild(bubble);
    messageWrapper.appendChild(bubbleRow);
    messagesContainerEl.appendChild(messageWrapper);
    messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
  }

  function appendLoadingMessage() {
    const loadingWrapper = document.createElement("div");
    loadingWrapper.id = "assistant-loading-bubble";
    loadingWrapper.className = "py-4 flex flex-col gap-y-2 text-foreground";

    const contentBox = document.createElement("div");
    contentBox.className = "flex items-center gap-x-2 text-sm text-muted-foreground-1";

    const pulseContainer = document.createElement("div");
    pulseContainer.className = "loading-dots flex items-center gap-x-1";

    for (let i = 0; i < 3; i++) {
      const dot = document.createElement("span");
      dot.className = "size-2 bg-primary rounded-full inline-block";
      pulseContainer.appendChild(dot);
    }

    const textSpan = document.createElement("span");
    textSpan.className = "ms-1 text-xs";
    textSpan.textContent = "Retrieving passages and generating answer...";

    contentBox.appendChild(pulseContainer);
    contentBox.appendChild(textSpan);
    loadingWrapper.appendChild(contentBox);
    messagesContainerEl.appendChild(loadingWrapper);
    messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
  }

  function removeLoadingMessage() {
    const el = document.getElementById("assistant-loading-bubble");
    if (el) el.remove();
  }

  function appendAssistantResponse(data) {
    const messageWrapper = document.createElement("div");
    messageWrapper.className = "py-4 flex flex-col gap-y-3 text-foreground border-b border-sidebar-line/30 last:border-0";

    const answerBox = document.createElement("div");
    answerBox.className = "text-sm leading-relaxed whitespace-pre-wrap text-foreground";
    answerBox.textContent = data.answer;
    messageWrapper.appendChild(answerBox);

    if (data.answer_found && data.sources && data.sources.length > 0) {
      const sourcesContainer = document.createElement("div");
      sourcesContainer.className = "mt-2 pt-2 border-t border-line-3/50";

      const sourcesHeader = document.createElement("div");
      sourcesHeader.className = "flex items-center gap-x-1.5 text-xs font-semibold text-muted-foreground-1 mb-2";

      const docIcon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      docIcon.setAttribute("class", "size-3.5 text-primary");
      docIcon.setAttribute("viewBox", "0 0 24 24");
      docIcon.setAttribute("fill", "none");
      docIcon.setAttribute("stroke", "currentColor");
      docIcon.setAttribute("stroke-width", "2");
      const dPath1 = document.createElementNS("http://www.w3.org/2000/svg", "path");
      dPath1.setAttribute("d", "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z");
      const dPath2 = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      dPath2.setAttribute("points", "14 2 14 8 20 8");
      docIcon.appendChild(dPath1);
      docIcon.appendChild(dPath2);
      sourcesHeader.appendChild(docIcon);

      const headerTitle = document.createElement("span");
      headerTitle.textContent = `Sources (${data.sources.length})`;
      sourcesHeader.appendChild(headerTitle);
      sourcesContainer.appendChild(sourcesHeader);

      const sourcesList = document.createElement("div");
      sourcesList.className = "grid grid-cols-1 sm:grid-cols-2 gap-2";

      data.sources.forEach((src) => {
        const card = document.createElement("div");
        card.className = "source-card flex items-start gap-x-2 p-2 bg-surface rounded-lg border border-line-3 text-xs";

        const cardIcon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        cardIcon.setAttribute("class", "shrink-0 size-4 text-muted-foreground-1 mt-0.5");
        cardIcon.setAttribute("viewBox", "0 0 24 24");
        cardIcon.setAttribute("fill", "none");
        cardIcon.setAttribute("stroke", "currentColor");
        cardIcon.setAttribute("stroke-width", "2");
        const cPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
        cPath.setAttribute("d", "M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z");
        cardIcon.appendChild(cPath);
        card.appendChild(cardIcon);

        const cardText = document.createElement("div");
        cardText.className = "min-w-0";

        const filenameP = document.createElement("p");
        filenameP.className = "font-medium text-foreground truncate";
        filenameP.textContent = src.filename;

        const locP = document.createElement("p");
        locP.className = "text-[11px] text-muted-foreground-1";
        if (src.page !== null && src.page !== undefined) {
          locP.textContent = `Page ${src.page} • ${src.chunk_id}`;
        } else {
          locP.textContent = `Section Reference • ${src.chunk_id}`;
        }

        cardText.appendChild(filenameP);
        cardText.appendChild(locP);
        card.appendChild(cardText);
        sourcesList.appendChild(card);
      });

      sourcesContainer.appendChild(sourcesList);
      messageWrapper.appendChild(sourcesContainer);
    }

    messagesContainerEl.appendChild(messageWrapper);
    messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
  }

  function appendErrorMessage(errorText) {
    const errorWrapper = document.createElement("div");
    errorWrapper.className = "py-3 px-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-x-2";

    const errIcon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    errIcon.setAttribute("class", "size-4 shrink-0");
    errIcon.setAttribute("viewBox", "0 0 24 24");
    errIcon.setAttribute("fill", "none");
    errIcon.setAttribute("stroke", "currentColor");
    errIcon.setAttribute("stroke-width", "2");
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", "12");
    circle.setAttribute("cy", "12");
    circle.setAttribute("r", "10");
    const line1 = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line1.setAttribute("x1", "12");
    line1.setAttribute("y1", "8");
    line1.setAttribute("x2", "12");
    line1.setAttribute("y2", "12");
    const line2 = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line2.setAttribute("x1", "12");
    line2.setAttribute("y1", "16");
    line2.setAttribute("x2", "12.01");
    line2.setAttribute("y2", "16");
    errIcon.appendChild(circle);
    errIcon.appendChild(line1);
    errIcon.appendChild(line2);

    const span = document.createElement("span");
    span.textContent = errorText;

    errorWrapper.appendChild(errIcon);
    errorWrapper.appendChild(span);
    messagesContainerEl.appendChild(errorWrapper);
    messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
  }

  async function submitQuestion() {
    if (isSubmitting) return;
    const question = questionInputEl.value.trim();
    if (!question) return;

    if (indexedDocuments.length === 0) {
      appendErrorMessage("Cannot ask question: no documents are currently indexed.");
      return;
    }

    isSubmitting = true;
    updateChatState();
    appendUserMessage(question);
    questionInputEl.value = "";
    appendLoadingMessage();

    try {
      const response = await fetch("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      removeLoadingMessage();

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error (${response.status})`);
      }

      const data = await response.json();
      appendAssistantResponse(data);
    } catch (err) {
      removeLoadingMessage();
      appendErrorMessage(err.message);
    } finally {
      isSubmitting = false;
      updateChatState();
      questionInputEl.focus();
    }
  }

  if (chatFormEl) {
    chatFormEl.addEventListener("submit", (e) => {
      e.preventDefault();
      submitQuestion();
    });
  }

  if (questionInputEl) {
    questionInputEl.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submitQuestion();
      }
    });
  }

  if (clearChatBtn) {
    clearChatBtn.addEventListener("click", () => {
      if (messagesContainerEl) messagesContainerEl.innerHTML = "";
      if (emptyStateEl) emptyStateEl.classList.remove("hidden");
    });
  }

  document.querySelectorAll(".prompt-suggestion-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (indexedDocuments.length === 0) return;
      const text = btn.textContent.trim();
      if (questionInputEl) {
        questionInputEl.value = text;
        submitQuestion();
      }
    });
  });

  fetchDocuments();
});
