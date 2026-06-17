/**
 * SettingsPanel — minimalist gear overlay for engine and voice settings.
 */

import { useState } from "react";
import type { AppSettings } from "../types";

interface Props {
  settings: AppSettings;
  onUpdate: (patch: Partial<AppSettings>) => void;
  engineConnected: boolean;
}

export default function SettingsPanel({ settings, onUpdate, engineConnected }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        className="settings-toggle"
        onClick={() => setOpen(!open)}
        title="Settings"
      >
        ⚙
      </button>

      {open && (
        <div className="settings-overlay" onClick={() => setOpen(false)}>
          <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
            <h3>Settings</h3>

            <label>
              Voice Profile
              <select
                value={settings.voiceProfile}
                onChange={(e) => onUpdate({ voiceProfile: e.target.value })}
              >
                <option value="new_york">New York Accent</option>
                <option value="default_female">Default Female</option>
                <option value="default_male">Default Male</option>
              </select>
            </label>

            <label>
              Correction Mode
              <select
                value={settings.correctionMode}
                onChange={(e) =>
                  onUpdate({
                    correctionMode: e.target.value as AppSettings["correctionMode"],
                  })
                }
              >
                <option value="off">Off</option>
                <option value="mild_only">Mild only</option>
                <option value="medium">Medium (default)</option>
                <option value="all">All — strict</option>
              </select>
            </label>

            <label>
              Engine URL
              <input
                type="text"
                value={settings.engineUrl}
                onChange={(e) => onUpdate({ engineUrl: e.target.value })}
              />
            </label>

            <div className="settings-status">
              Engine:{" "}
              <span className={engineConnected ? "status-ok" : "status-err"}>
                {engineConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
