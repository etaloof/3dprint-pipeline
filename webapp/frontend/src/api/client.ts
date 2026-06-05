export interface Material {
  id: string;
  name: string;
  wall_min_mm?: number;
  temp_max_service?: number;
}

export interface Session {
  id: string;
  material: string;
  pipeline_mode: string;
  onshape: { document_id: string; workspace_id: string; element_id: string };
  metadata: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  claude_mode: string;
  claude_cli: boolean;
  mcp_proxy: boolean;
  cadquery: boolean;
  pipeline_mode: string;
}

const API_BASE = "";

export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function getMaterials(): Promise<Material[]> {
  const res = await fetch(`${API_BASE}/api/materials`);
  const data = await res.json();
  return data.materials;
}

export async function createSession(material: string): Promise<Session> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ material }),
  });
  if (!res.ok) throw new Error("Failed to create session");
  const data = await res.json();
  return data.session;
}

export async function sendMessage(sessionId: string, content: string): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
}

export async function listFiles(sessionId: string): Promise<Array<{ name: string; url: string; format: string }>> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/files`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.files ?? [];
}
