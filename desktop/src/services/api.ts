/**
 * REST API client for the VoxLingua engine.
 */
import type { EngineStatus } from "../types";

const DEFAULT_BASE = "http://localhost:9876";

export class ApiClient {
  private base: string;

  constructor(base: string = DEFAULT_BASE) {
    this.base = base.replace(/\/+$/, "");
  }

  async getStatus(): Promise<EngineStatus> {
    const res = await fetch(`${this.base}/api/status`);
    if (!res.ok) throw new Error(`Status API: ${res.status}`);
    return res.json();
  }

  async getVoices(): Promise<{ voices: Array<{ profile_id: string; name: string }> }> {
    const res = await fetch(`${this.base}/api/voices`);
    if (!res.ok) throw new Error(`Voices API: ${res.status}`);
    return res.json();
  }

  async getScenes(): Promise<{ scenes: Array<{ id: string; name: string }> }> {
    const res = await fetch(`${this.base}/api/scenes`);
    if (!res.ok) throw new Error(`Scenes API: ${res.status}`);
    return res.json();
  }

  setBaseUrl(url: string) {
    this.base = url.replace(/\/+$/, "");
  }
}

export const apiClient = new ApiClient();
