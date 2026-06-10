import type { PipelineEvent } from "../api/sse";

export class ChatPanel {
  private listEl: HTMLElement;
  private assistantBuffer = "";
  private assistantEl: HTMLElement | null = null;

  constructor(listEl: HTMLElement) {
    this.listEl = listEl;
  }

  addUserMessage(text: string): void {
    this.flushAssistant();
    this.append("user", text);
  }

  addSystem(text: string): void {
    this.append("system", text);
  }

  handleEvent(event: PipelineEvent): void {
    switch (event.type) {
      case "assistant_delta":
        if (event.text) this.appendAssistantDelta(event.text);
        break;
      case "reasoning":
        this.append("system", `Reasoning: ${event.text ?? ""}`);
        break;
      case "phase":
        this.append("system", `Phase: ${event.phase}${event.text ? ` — ${event.text}` : ""}`);
        break;
      case "tool_call":
        this.append("tool", `🔧 ${event.name ?? event.summary ?? "tool"}`);
        break;
      case "tool_result":
        this.append("tool", `${event.ok ? "✅" : "❌"} ${event.name ?? "tool"}: ${event.summary ?? ""}`);
        break;
      case "file":
        this.append("system", `File ready: ${event.format?.toUpperCase()} → ${event.url}`);
        break;
      case "error":
        this.append("error", event.message ?? "Unknown error");
        break;
      case "done":
        this.flushAssistant();
        this.append("system", `Job ${event.status ?? "completed"}`);
        break;
      default:
        break;
    }
  }

  private appendAssistantDelta(text: string): void {
    if (!this.assistantEl) {
      this.assistantEl = document.createElement("div");
      this.assistantEl.className = "message assistant";
      this.listEl.appendChild(this.assistantEl);
      this.assistantBuffer = "";
    }
    this.assistantBuffer += text;
    this.assistantEl.textContent = this.assistantBuffer;
    this.listEl.scrollTop = this.listEl.scrollHeight;
  }

  private flushAssistant(): void {
    this.assistantEl = null;
    this.assistantBuffer = "";
  }

  private append(kind: string, text: string): void {
    const el = document.createElement("div");
    el.className = `message ${kind}`;
    el.textContent = text;
    this.listEl.appendChild(el);
    this.listEl.scrollTop = this.listEl.scrollHeight;
  }

  clear(): void {
    this.listEl.innerHTML = "";
    this.flushAssistant();
  }
}
