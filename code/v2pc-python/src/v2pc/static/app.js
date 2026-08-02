(() => {
  "use strict";

  const expression = document.querySelector("#expression");
  const controls = document.querySelector("#variable-controls");
  const assignment = document.querySelector("#assignment");
  const emptyMessage = document.querySelector("#variables-empty");
  const form = expression?.closest("form");
  const constructionSeed = document.querySelector("#construction-seed");
  const constructionExpression = document.querySelector("#construction-expression");
  const constructionSide = document.querySelector("#construction-side");
  const side = form?.querySelector('input[name="side"]');
  const buildAllShares = document.querySelector("#build-all-shares");

  if (!expression || !controls || !assignment || !emptyMessage || !form) {
    return;
  }

  const variablePattern = /\b[A-Za-z][A-Za-z0-9_]*\b/g;

  function currentValues() {
    const values = new Map();
    controls.querySelectorAll("[data-variable]").forEach((fieldset) => {
      const selected = fieldset.querySelector("input:checked");
      values.set(fieldset.dataset.variable, selected?.value ?? "0");
    });
    return values;
  }

  function variablesIn(text) {
    const unique = new Set(text.match(variablePattern) ?? []);
    return [...unique];
  }

  function syncAssignment() {
    assignment.value = [...controls.querySelectorAll("[data-variable]")]
      .map((fieldset) => {
        const selected = fieldset.querySelector("input:checked");
        return `${fieldset.dataset.variable}=${selected?.value ?? "0"}`;
      })
      .join(",");
  }

  function choice(variable, index, value) {
    const fieldset = document.createElement("fieldset");
    fieldset.className = "variable-choice";
    fieldset.dataset.variable = variable;

    const legend = document.createElement("legend");
    legend.textContent = variable;
    fieldset.append(legend);

    const choices = document.createElement("div");
    for (const bit of ["0", "1"]) {
      const label = document.createElement("label");
      const input = document.createElement("input");
      const visibleBit = document.createElement("span");
      input.type = "radio";
      input.name = `variable_${index}`;
      input.value = bit;
      input.checked = bit === value;
      visibleBit.textContent = bit;
      label.append(input, visibleBit);
      choices.append(label);
    }
    fieldset.append(choices);
    return fieldset;
  }

  function renderVariables() {
    const previous = currentValues();
    const variables = variablesIn(expression.value);
    controls.replaceChildren(
      ...variables.map((variable, index) =>
        choice(variable, index, previous.get(variable) ?? "0")
      )
    );
    emptyMessage.hidden = variables.length > 0;
    syncAssignment();
  }

  let updateTimer;
  expression.addEventListener("input", () => {
    window.clearTimeout(updateTimer);
    updateTimer = window.setTimeout(renderVariables, 120);
  });
  controls.addEventListener("change", syncAssignment);
  async function downloadAllShares(event) {
    event.preventDefault();
    syncAssignment();
    buildAllShares.disabled = true;
    let archiveUrl;
    try {
      const response = await fetch(buildAllShares.formAction, {
        method: "POST",
        body: new FormData(form),
      });
      if (!response.ok) {
        throw new Error((await response.text()).trim() || "Download non riuscito.");
      }

      const effectiveSeed = response.headers.get("X-V2PC-Seed");
      if (effectiveSeed && constructionSeed && constructionExpression && constructionSide) {
        constructionSeed.value = effectiveSeed;
        constructionExpression.value = expression.value.trim();
        constructionSide.value = side?.value ?? "";
      }

      archiveUrl = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = archiveUrl;
      link.download = "v2pc-tutte-le-alternative.zip";
      link.hidden = true;
      document.body.append(link);
      link.click();
      link.remove();
    } catch (error) {
      window.alert(error instanceof Error ? error.message : "Download non riuscito.");
    } finally {
      if (archiveUrl) {
        window.setTimeout(() => URL.revokeObjectURL(archiveUrl), 1000);
      }
      buildAllShares.disabled = false;
    }
  }

  form.addEventListener("submit", (event) => {
    syncAssignment();
    if (event.submitter === buildAllShares) {
      downloadAllShares(event);
    }
  });
  syncAssignment();

  function fitCircuit() {
    const viewport = document.querySelector(".circuit-scroll");
    const stage = document.querySelector(".circuit-stage");
    if (!viewport || !stage) {
      return;
    }

    stage.style.transform = "none";
    stage.style.marginLeft = "0px";
    const naturalWidth = stage.scrollWidth;
    const naturalHeight = stage.scrollHeight;
    const availableWidth = Math.max(1, viewport.clientWidth - 4);
    const scale = Math.min(1, availableWidth / naturalWidth);
    const centeredOffset = Math.max(0, (availableWidth - naturalWidth * scale) / 2);

    stage.style.transformOrigin = "top left";
    stage.style.transform = `scale(${scale})`;
    stage.style.marginLeft = `${centeredOffset}px`;
    viewport.style.height = `${Math.ceil(naturalHeight * scale)}px`;
  }

  window.addEventListener("load", fitCircuit);
  window.addEventListener("resize", fitCircuit);
  if ("ResizeObserver" in window) {
    new ResizeObserver(fitCircuit).observe(document.querySelector("main"));
  }
  window.requestAnimationFrame(fitCircuit);

  const circuitDownload = document.querySelector("#download-circuit");
  const circuitDownloadStatus = document.querySelector("#download-circuit-status");

  function imagesReady(stage) {
    return Promise.all(
      [...stage.querySelectorAll("img")].map((image) => {
        if (image.complete && image.naturalWidth > 0) {
          return Promise.resolve();
        }
        return new Promise((resolve, reject) => {
          image.addEventListener("load", resolve, { once: true });
          image.addEventListener(
            "error",
            () => reject(new Error("Una share del circuito non è caricabile.")),
            { once: true }
          );
        });
      })
    );
  }

  function canvasBlob(canvas) {
    return new Promise((resolve, reject) => {
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error("Il browser non riesce a creare il file PNG."));
          }
        },
        "image/png"
      );
    });
  }

  function relativeRect(element, stageRect) {
    const rect = element.getBoundingClientRect();
    return {
      x: rect.left - stageRect.left,
      y: rect.top - stageRect.top,
      width: rect.width,
      height: rect.height,
      right: rect.right - stageRect.left,
      bottom: rect.bottom - stageRect.top,
      centerX: rect.left - stageRect.left + rect.width / 2,
      centerY: rect.top - stageRect.top + rect.height / 2,
    };
  }

  function roundedRectangle(context, rect, radii = 0) {
    const raw = Array.isArray(radii) ? radii : [radii, radii, radii, radii];
    const [topLeft, topRight, bottomRight, bottomLeft] = raw.map((radius) =>
      Math.max(0, Math.min(radius, rect.width / 2, rect.height / 2))
    );

    context.beginPath();
    context.moveTo(rect.x + topLeft, rect.y);
    context.lineTo(rect.right - topRight, rect.y);
    context.quadraticCurveTo(rect.right, rect.y, rect.right, rect.y + topRight);
    context.lineTo(rect.right, rect.bottom - bottomRight);
    context.quadraticCurveTo(
      rect.right,
      rect.bottom,
      rect.right - bottomRight,
      rect.bottom
    );
    context.lineTo(rect.x + bottomLeft, rect.bottom);
    context.quadraticCurveTo(
      rect.x,
      rect.bottom,
      rect.x,
      rect.bottom - bottomLeft
    );
    context.lineTo(rect.x, rect.y + topLeft);
    context.quadraticCurveTo(rect.x, rect.y, rect.x + topLeft, rect.y);
    context.closePath();
  }

  function visibleColor(color) {
    return color && color !== "rgba(0, 0, 0, 0)" && color !== "transparent";
  }

  function drawElementBox(context, element, stageRect, radius = 0) {
    const rect = relativeRect(element, stageRect);
    const style = window.getComputedStyle(element);
    if (visibleColor(style.backgroundColor)) {
      roundedRectangle(context, rect, radius);
      context.fillStyle = style.backgroundColor;
      context.fill();
    }

    const borderWidth = Number.parseFloat(style.borderTopWidth);
    if (borderWidth > 0 && visibleColor(style.borderTopColor)) {
      roundedRectangle(context, rect, radius);
      context.strokeStyle = style.borderTopColor;
      context.lineWidth = borderWidth;
      context.stroke();
    }
    return rect;
  }

  function drawElementText(context, element, stageRect) {
    const text = element.textContent.trim();
    if (!text) {
      return;
    }
    const rect = relativeRect(element, stageRect);
    const style = window.getComputedStyle(element);
    context.save();
    context.fillStyle = style.color;
    context.font = style.font;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(text, rect.centerX, rect.centerY);
    context.restore();
  }

  function drawCircuitImage(context, image, stageRect) {
    const rect = relativeRect(image, stageRect);
    const style = window.getComputedStyle(image);
    const borderWidth = Number.parseFloat(style.borderTopWidth) || 0;
    context.save();
    context.fillStyle = style.backgroundColor || "#ffffff";
    context.fillRect(rect.x, rect.y, rect.width, rect.height);
    context.imageSmoothingEnabled = false;
    context.drawImage(
      image,
      rect.x + borderWidth,
      rect.y + borderWidth,
      Math.max(1, rect.width - borderWidth * 2),
      Math.max(1, rect.height - borderWidth * 2)
    );
    if (borderWidth > 0 && visibleColor(style.borderTopColor)) {
      context.strokeStyle = style.borderTopColor;
      context.lineWidth = borderWidth;
      context.strokeRect(rect.x, rect.y, rect.width, rect.height);
    }
    context.restore();
  }

  function drawCircuitConnections(context, stage, stageRect) {
    const ink = window.getComputedStyle(stage).getPropertyValue("--ink").trim();
    context.save();
    context.strokeStyle = ink || "#171717";
    context.lineWidth = 1.5;
    context.lineCap = "square";
    context.lineJoin = "round";

    const marker = stage.querySelector(".circuit-output-marker");
    const root = stage.querySelector(".circuit-tree > ul > li > .circuit-node");
    if (marker && root) {
      const markerRect = relativeRect(marker, stageRect);
      const rootRect = relativeRect(root, stageRect);
      context.beginPath();
      context.moveTo(markerRect.centerX, markerRect.bottom);
      context.lineTo(rootRect.centerX, rootRect.y);
      context.stroke();
    }

    stage.querySelectorAll(".circuit-branch").forEach((branch) => {
      const parent = branch.querySelector(":scope > .circuit-node");
      const children = [
        ...branch.querySelectorAll(":scope > ul > li > .circuit-node"),
      ];
      if (!parent || children.length === 0) {
        return;
      }

      const parentRect = relativeRect(parent, stageRect);
      const childRects = children.map((child) => relativeRect(child, stageRect));
      const joinY = Math.min(...childRects.map((rect) => rect.y)) - 25;
      context.beginPath();
      context.moveTo(parentRect.centerX, parentRect.bottom);
      context.lineTo(parentRect.centerX, joinY);
      if (childRects.length > 1) {
        context.lineTo(childRects[0].centerX, joinY);
        context.moveTo(parentRect.centerX, joinY);
        context.lineTo(childRects[childRects.length - 1].centerX, joinY);
      }
      childRects.forEach((rect) => {
        context.moveTo(rect.centerX, joinY);
        context.lineTo(rect.centerX, rect.y);
      });
      context.stroke();
    });
    context.restore();
  }

  function drawGate(context, gate, stageRect) {
    const rect = relativeRect(gate, stageRect);
    const style = window.getComputedStyle(gate);
    let radii = [3, 22, 22, 3];
    if (gate.classList.contains("gate-symbol--or")) {
      radii = [rect.height / 2, 22, 22, rect.height / 2];
    }
    if (gate.classList.contains("gate-symbol--xor")) {
      radii = [rect.height / 2, 22, 22, rect.height / 2];
      context.save();
      context.strokeStyle = style.borderTopColor;
      context.lineWidth = 1.5;
      context.beginPath();
      context.moveTo(rect.x - 5, rect.y + 1);
      context.quadraticCurveTo(
        rect.x + 7,
        rect.centerY,
        rect.x - 5,
        rect.bottom - 1
      );
      context.stroke();
      context.restore();
    }
    if (gate.classList.contains("gate-symbol--not")) {
      radii = rect.height / 2;
    }

    roundedRectangle(context, rect, radii);
    context.fillStyle = style.backgroundColor;
    context.fill();
    context.strokeStyle = style.borderTopColor;
    context.lineWidth = Number.parseFloat(style.borderTopWidth) || 1.5;
    context.stroke();
    const label = gate.querySelector("span");
    if (label) {
      drawElementText(context, label, stageRect);
    }
  }

  function drawCircuitContent(context, stage, stageRect) {
    const marker = stage.querySelector(".circuit-output-marker");
    if (marker) {
      drawElementBox(context, marker, stageRect, 6);
      marker.querySelectorAll(":scope > span, :scope > strong").forEach((text) =>
        drawElementText(context, text, stageRect)
      );
    }

    stage.querySelectorAll(".circuit-node--input").forEach((input) => {
      drawElementBox(context, input, stageRect, 7);
      input.querySelectorAll(".circuit-input-heading > *").forEach((text) =>
        drawElementText(context, text, stageRect)
      );
      const share = input.querySelector(".mini-share-image");
      if (share) {
        drawCircuitImage(context, share, stageRect);
      }
      const pointer = input.querySelector(".mini-pointer");
      if (pointer) {
        drawElementBox(context, pointer, stageRect, 5);
        pointer.querySelectorAll(":scope > div > span, :scope > .no-pointer").forEach(
          (text) => drawElementText(context, text, stageRect)
        );
        pointer.querySelectorAll(".pointer-block").forEach((block) => {
          drawElementBox(context, block, stageRect);
          block.querySelectorAll(".pointer-subpixel").forEach((pixel) =>
            drawElementBox(context, pixel, stageRect)
          );
        });
      }
    });

    stage.querySelectorAll(".gate-symbol").forEach((gate) =>
      drawGate(context, gate, stageRect)
    );
    stage.querySelectorAll(".gate-output").forEach((output) => {
      const image = output.querySelector("img");
      const label = output.querySelector("span");
      if (image) {
        drawCircuitImage(context, image, stageRect);
      }
      if (label) {
        drawElementText(context, label, stageRect);
      }
    });
  }

  async function downloadVisibleCircuit() {
    const stage = document.querySelector(".circuit-stage");
    if (!stage || !circuitDownload || !circuitDownloadStatus) {
      return;
    }

    circuitDownload.disabled = true;
    circuitDownloadStatus.textContent = "Preparazione del PNG…";
    let pngUrl;
    const previousTransform = stage.style.transform;
    const previousMargin = stage.style.marginLeft;
    try {
      await imagesReady(stage);
      const padding = 28;
      stage.style.transform = "none";
      stage.style.marginLeft = "0";
      const stageRect = stage.getBoundingClientRect();
      const width = Math.ceil(stage.scrollWidth + padding * 2);
      const height = Math.ceil(stage.scrollHeight + padding * 2);
      const scale = 2;
      const canvas = document.createElement("canvas");
      canvas.width = width * scale;
      canvas.height = height * scale;
      const context = canvas.getContext("2d");
      if (!context) {
        throw new Error("Il browser non rende disponibile il disegno 2D.");
      }
      context.scale(scale, scale);
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, width, height);
      context.translate(padding, padding);
      drawCircuitConnections(context, stage, stageRect);
      drawCircuitContent(context, stage, stageRect);

      const png = await canvasBlob(canvas);
      pngUrl = URL.createObjectURL(png);
      const link = document.createElement("a");
      link.href = pngUrl;
      link.download = "v2pc-circuito.png";
      link.hidden = true;
      document.body.append(link);
      link.click();
      link.remove();
      circuitDownloadStatus.textContent = "Immagine scaricata.";
    } catch (error) {
      circuitDownloadStatus.textContent =
        error instanceof Error ? error.message : "Download non riuscito.";
    } finally {
      if (pngUrl) {
        window.setTimeout(() => URL.revokeObjectURL(pngUrl), 1000);
      }
      stage.style.transform = previousTransform;
      stage.style.marginLeft = previousMargin;
      circuitDownload.disabled = false;
    }
  }

  circuitDownload?.addEventListener("click", downloadVisibleCircuit);
})();
