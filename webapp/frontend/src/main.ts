import {
  createSession,
  getHealth,
  getMaterials,
  listFiles,
  sendMessage,
  type Session,
} from "./api/client";
import { streamJob } from "./api/sse";
import { ChatPanel } from "./components/ChatPanel";
import { Viewer3D } from "./components/Viewer3D";

const materialSelect = document.getElementById("material-select") as HTMLSelectElement;
const sessionBadge = document.getElementById("session-badge")!;
const pipelineBadge = document.getElementById("pipeline-badge")!;
const jobStatus = document.getElementById("job-status")!;
const healthStatus = document.getElementById("health-status")!;
const messageList = document.getElementById("message-list")!;
const chatForm = document.getElementById("chat-form") as HTMLFormElement;
const promptInput = document.getElementById("prompt-input") as HTMLTextAreaElement;
const sendBtn = document.getElementById("send-btn") as HTMLButtonElement;
const newSessionBtn = document.getElementById("new-session-btn") as HTMLButtonElement;
const exportStlBtn = document.getElementById("export-stl-btn") as HTMLButtonElement;
const exportStepBtn = document.getElementById("export-step-btn") as HTMLButtonElement;
const onshapeLink = document.getElementById("onshape-link") as HTMLAnchorElement;
const viewerContainer = document.getElementById("viewer-container")!;

const chat = new ChatPanel(messageList);
const viewer = new Viewer3D(viewerContainer);

let session: Session | null = null;
let closeStream: (() => void) | null = null;
let stlUrl = "";
let stepUrl = "";

async function init(): Promise<void> {
  await loadMaterials();
  await checkHealth();
  await ensureSession();
  bindEvents();
}

async function loadMaterials(): Promise<void> {
  try {
    const materials = await getMaterials();
    materialSelect.innerHTML = materials
      .map((m) => `<option value="${m.id}">${m.id} — ${m.name}</option>`)
      .join("");
  } catch {
    materialSelect.innerHTML = '<option value="PLA">PLA</option>';
  }
}

async function checkHealth(): Promise<void> {
  try {
    const h = await getHealth();
    healthStatus.textContent = `API ok · claude=${h.claude_mode} · cadquery=${h.cadquery} · mcp=${h.mcp_proxy}`;
    pipelineBadge.textContent = h.claude_mode;
  } catch {
    healthStatus.textContent = "API unreachable";
  }
}

async function ensureSession(): Promise<void> {
  const stored = localStorage.getItem("pipeline_session_id");
  if (stored) {
    session = { id: stored } as Session;
    sessionBadge.textContent = stored.slice(0, 8) + "…";
    await refreshFiles();
    return;
  }
  await createNewSession();
}

async function createNewSession(): Promise<void> {
  session = await createSession(materialSelect.value);
  localStorage.setItem("pipeline_session_id", session.id);
  sessionBadge.textContent = session.id.slice(0, 8) + "…";
  pipelineBadge.textContent = String(session.metadata?.resolved_pipeline ?? session.pipeline_mode);
  chat.clear();
  viewer.clear();
  stlUrl = "";
  stepUrl = "";
  updateExportButtons();
  chat.addSystem("New session started. Describe the part you want to print.");
}

function bindEvents(): void {
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = promptInput.value.trim();
    if (!text || !session) return;

    sendBtn.disabled = true;
    chat.addUserMessage(text);
    promptInput.value = "";
    jobStatus.textContent = "Running…";

    try {
      const { job_id } = await sendMessage(session.id, text);
      closeStream?.();
      closeStream = streamJob(
        session.id,
        job_id,
        async (event) => {
          chat.handleEvent(event);
          if (event.type === "file" && event.url) {
            if (event.format === "stl") {
              stlUrl = event.url;
              await viewer.loadStl(event.url);
            }
            if (event.format === "step") stepUrl = event.url;
            updateExportButtons();
          }
          if (event.type === "done") {
            jobStatus.textContent = "Ready";
            sendBtn.disabled = false;
            await refreshFiles();
          }
        },
        () => {
          jobStatus.textContent = "Stream ended";
          sendBtn.disabled = false;
        },
      );
    } catch (err) {
      chat.addSystem(`Error: ${(err as Error).message}`);
      sendBtn.disabled = false;
      jobStatus.textContent = "Error";
    }
  });

  newSessionBtn.addEventListener("click", () => {
    localStorage.removeItem("pipeline_session_id");
    createNewSession();
  });

  exportStlBtn.addEventListener("click", () => {
    if (stlUrl) window.open(stlUrl, "_blank");
  });
  exportStepBtn.addEventListener("click", () => {
    if (stepUrl) window.open(stepUrl, "_blank");
  });
}

async function refreshFiles(): Promise<void> {
  if (!session) return;
  const files = await listFiles(session.id);
  for (const f of files) {
    if (f.format === "stl") {
      stlUrl = f.url;
      try {
        await viewer.loadStl(f.url);
      } catch {
        // viewer may fail if no geometry yet
      }
    }
    if (f.format === "step") stepUrl = f.url;
  }
  updateExportButtons();
}

function updateExportButtons(): void {
  exportStlBtn.disabled = !stlUrl;
  exportStepBtn.disabled = !stepUrl;

  if (session?.onshape?.document_id) {
    const { document_id, workspace_id, element_id } = session.onshape;
    onshapeLink.href = `https://cad.onshape.com/documents/${document_id}/w/${workspace_id}/e/${element_id}`;
    onshapeLink.classList.remove("hidden");
  }
}

init();
