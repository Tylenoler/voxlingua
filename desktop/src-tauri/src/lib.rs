use tauri::Manager;

/// Default Python engine URL. The sidecar will be managed separately.
const ENGINE_URL: &str = "http://localhost:9876";

#[tauri::command]
fn get_engine_url() -> String {
    ENGINE_URL.to_string()
}

#[tauri::command]
fn get_ws_url() -> String {
    "ws://localhost:9876/ws/mobile".to_string()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![get_engine_url, get_ws_url])
        .run(tauri::generate_context!())
        .expect("error while running VoxLingua desktop");
}
