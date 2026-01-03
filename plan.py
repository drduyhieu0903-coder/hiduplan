import streamlit as st
import streamlit.components.v1 as components
import trimesh
import os
import zipfile
import tempfile
import base64
import shutil

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="HIDU - Surgical Planning Studio")

st.markdown("""
<style>
    .stApp { background-color: #0a0e27; color: #e8eaf6; }
    h1 { color: #ffffff !important; font-weight: 300 !important; letter-spacing: 2px; }
    .stFileUploader { 
        border: 2px dashed #3949ab; 
        border-radius: 12px; 
        background: rgba(57, 73, 171, 0.05);
        padding: 20px;
    }
    section[data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #1a237e 0%, #0d47a1 100%);
        color: white;
    }
    .stButton>button {
        background: linear-gradient(135deg, #1976d2 0%, #2196f3 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 500;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.4);
    }
</style>
""", unsafe_allow_html=True)

st.title("⚕️ HIDU: Medical Surgical Planning Studio")

if 'scale_factor' not in st.session_state:
    st.session_state['scale_factor'] = 1.0

# --- BACKEND ---
@st.cache_data(show_spinner=False)
def process_file_high_quality(uploaded_file):
    temp_dir = tempfile.mkdtemp()
    extract_path = os.path.join(temp_dir, "extracted")
    os.makedirs(extract_path, exist_ok=True)
    
    with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    
    obj_file = None
    mtl_file = None
    tex_file = None
    
    for root, dirs, files in os.walk(extract_path):
        for file in files:
            if file.lower().endswith('.obj'):
                obj_file = os.path.join(root, file)
            elif file.lower().endswith('.mtl'):
                mtl_file = os.path.join(root, file)
            elif file.lower().endswith(('.jpg', '.jpeg', '.png')):
                tex_file = os.path.join(root, file)

    if not obj_file:
        return None, None, "❌ No .obj file found"
    
    mesh = trimesh.load(obj_file, force='mesh')
    mesh.apply_translation(-mesh.centroid) 
    obj_str = mesh.export(file_type='obj')
    
    mtl_content = ""
    if mtl_file and tex_file:
        try:
            with open(tex_file, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode()
            mime = "image/png" if tex_file.lower().endswith('.png') else "image/jpeg"
            data_uri = f"data:{mime};base64,{b64_img}"
            with open(mtl_file, "r", encoding='utf-8', errors='ignore') as f:
                raw_mtl = f.read()
            lines = []
            for line in raw_mtl.splitlines():
                if line.strip().startswith("map_Kd"):
                    lines.append(f"map_Kd {data_uri}")
                else:
                    lines.append(line)
            mtl_content = "\n".join(lines)
        except:
            mtl_content = ""
            
    shutil.rmtree(temp_dir)
    return obj_str, mtl_content, None

# --- FRONTEND: MEDICAL GRADE 3D VIEWER ---
def render_studio_viewer(obj_text, mtl_text, scale_factor, height=750):
    if isinstance(obj_text, bytes): obj_text = obj_text.decode('utf-8')
    b64_obj = base64.b64encode(obj_text.encode('utf-8')).decode('utf-8')
    b64_mtl = base64.b64encode(mtl_text.encode('utf-8')).decode('utf-8')
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                overflow: hidden; 
                background: linear-gradient(135deg, #0a0e27 0%, #1a237e 100%);
                font-family: 'Segoe UI', 'Roboto', sans-serif; 
                user-select: none;
                -webkit-user-select: none;
                -webkit-touch-callout: none;
                touch-action: none;
            }}
            canvas {{ 
                width: 100%; 
                height: 100%; 
                display: block; 
                outline: none;
                touch-action: none;
            }}
            
            /* PROFESSIONAL MEDICAL TOOLBAR */
            .toolbar {{
                position: absolute; top: 20px; left: 20px;
                background: linear-gradient(135deg, rgba(13, 71, 161, 0.95), rgba(25, 118, 210, 0.95));
                backdrop-filter: blur(15px);
                border-radius: 16px;
                padding: 12px;
                border: 2px solid rgba(255,255,255,0.15);
                display: flex; flex-direction: column; gap: 10px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                width: 60px;
                z-index: 100;
                touch-action: none;
            }}
            
            .tool-btn {{
                width: 48px; height: 48px;
                border-radius: 12px; border: none;
                background: rgba(255,255,255,0.1); 
                color: #e3f2fd;
                cursor: pointer; 
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                display: flex; align-items: center; justify-content: center;
                touch-action: none;
            }}
            .tool-btn:hover {{ 
                background: rgba(255,255,255,0.2); 
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(33,150,243,0.4);
            }}
            .tool-btn.active {{ 
                background: linear-gradient(135deg, #2196f3, #1976d2);
                box-shadow: 0 4px 20px rgba(33,150,243,0.6);
                transform: scale(1.05);
            }}
            .tool-btn i {{ font-size: 24px; }}
            
            .divider {{ height: 2px; background: rgba(255,255,255,0.2); margin: 5px 0; border-radius: 1px; }}

            /* SETTINGS PANEL */
            .settings-panel {{
                position: absolute; top: 20px; left: 95px;
                background: linear-gradient(135deg, rgba(13, 71, 161, 0.95), rgba(25, 118, 210, 0.95));
                backdrop-filter: blur(15px);
                border-radius: 16px;
                padding: 20px;
                border: 2px solid rgba(255,255,255,0.15);
                color: white; 
                width: 280px;
                display: none;
                flex-direction: column; 
                gap: 16px;
                z-index: 99;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                touch-action: none;
            }}
            
            .panel-header {{
                font-weight: 600;
                font-size: 14px;
                color: #e3f2fd;
                letter-spacing: 1px;
                text-transform: uppercase;
                border-bottom: 2px solid rgba(255,255,255,0.2);
                padding-bottom: 10px;
                margin-bottom: 5px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .close-panel-btn {{
                width: 24px;
                height: 24px;
                border-radius: 50%;
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                font-size: 18px;
                line-height: 1;
                padding: 0;
            }}
            
            .close-panel-btn:hover {{
                background: rgba(244,67,54,0.8);
                transform: scale(1.1);
            }}
            
            .setting-row {{ 
                display: flex; 
                align-items: center; 
                justify-content: space-between; 
                font-size: 13px;
                padding: 8px 0;
            }}
            
            .setting-label {{
                color: #e3f2fd;
                font-weight: 500;
            }}
            
            /* Medical Color Presets */
            .color-presets {{
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 8px;
                margin: 10px 0;
            }}
            
            .color-preset {{
                width: 36px;
                height: 36px;
                border-radius: 8px;
                cursor: pointer;
                border: 2px solid transparent;
                transition: all 0.2s;
                touch-action: none;
            }}
            
            .color-preset:hover {{
                transform: scale(1.1);
                border-color: white;
            }}
            
            .color-preset.active {{
                border-color: white;
                box-shadow: 0 0 12px currentColor;
            }}
            
            .slider {{ 
                width: 140px; 
                height: 6px;
                border-radius: 3px;
                background: rgba(255,255,255,0.2);
                outline: none;
                -webkit-appearance: none;
            }}
            
            .slider::-webkit-slider-thumb {{
                -webkit-appearance: none;
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background: #2196f3;
                cursor: pointer;
                box-shadow: 0 2px 8px rgba(33,150,243,0.5);
            }}
            
            .value-display {{
                min-width: 45px;
                text-align: right;
                font-weight: 600;
                color: #64b5f6;
            }}
            
            /* MEASUREMENT DISPLAY */
            .measurement-box {{
                background: rgba(0,0,0,0.7);
                border: 2px solid #4caf50;
                border-radius: 12px;
                padding: 16px;
                margin-top: 10px;
                text-align: center;
            }}
            
            .measurement-label {{
                font-size: 11px;
                color: #a5d6a7;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 5px;
            }}
            
            .measurement-value {{
                font-size: 24px;
                font-weight: 700;
                color: #4caf50;
                text-shadow: 0 0 10px rgba(76,175,80,0.5);
            }}

            /* HUD INFO */
            .info-hud {{
                position: absolute; 
                bottom: 30px; 
                left: 50%; 
                transform: translateX(-50%);
                background: rgba(0,0,0,0.8); 
                color: white;
                padding: 12px 24px; 
                border-radius: 24px; 
                font-size: 13px;
                pointer-events: none; 
                opacity: 0; 
                transition: opacity 0.3s;
                border: 1px solid rgba(255,255,255,0.2);
            }}
            .info-hud.visible {{ opacity: 1; }}

            /* ANNOTATION LABEL - CẬP NHẬT MỚI */
            .annotation-label {{
                position: absolute;
                color: white;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                pointer-events: all;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                border: 1px solid rgba(255,255,255,0.4);
                min-width: 140px;
                touch-action: none;
                user-select: none;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                transition: transform 0.1s;
                z-index: 1000;
            }}
            
            .annotation-header {{
                padding: 6px 10px;
                cursor: grab;
                display: flex;
                align-items: center;
                justify-content: space-between;
                background: rgba(0,0,0,0.2);
            }}

            .annotation-header:active {{
                cursor: grabbing;
            }}
            
            .annotation-body {{
                padding: 8px;
                background: inherit;
            }}
            
            .annotation-number {{
                display: flex;
                align-items: center;
                justify-content: center;
                width: 20px;
                height: 20px;
                background: white;
                color: #333;
                border-radius: 50%;
                font-size: 11px;
                font-weight: bold;
                margin-right: 8px;
            }}
            
            .annotation-input {{
                background: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.3);
                color: inherit;
                padding: 4px 8px;
                border-radius: 4px;
                width: 100%;
                font-size: 11px;
                outline: none;
            }}
            
            .annotation-input::placeholder {{
                color: rgba(255,255,255,0.6);
            }}
            
            /* FLOATING MEASUREMENT LABELS */
            .floating-label {{
                position: absolute;
                background: rgba(76, 175, 80, 0.95);
                color: white;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 700;
                pointer-events: all;
                z-index: 1000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
                border: 2px solid rgba(255,255,255,0.5);
                white-space: nowrap;
                cursor: grab;
                user-select: none;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .floating-label:active {{
                cursor: grabbing;
            }}
            
            .floating-label.distance {{
                background: rgba(33, 150, 243, 0.95);
            }}
            
            .floating-label.angle {{
                background: rgba(255, 152, 0, 0.95);
            }}
            
            .floating-label.area {{
                background: rgba(156, 39, 176, 0.95);
                font-size: 15px;
            }}
            
            .label-close-btn {{
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: rgba(244, 67, 54, 0.9);
                border: none;
                color: white;
                font-size: 12px;
                font-weight: bold;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.2s;
                padding: 0;
                line-height: 1;
            }}
            
            .label-close-btn:hover {{
                background: rgba(244, 67, 54, 1);
                transform: scale(1.1);
            }}
            
            /* EXPORT BUTTONS */
            .export-panel {{
                position: absolute;
                bottom: 20px;
                right: 20px;
                display: flex;
                flex-direction: column;
                gap: 10px;
                z-index: 100;
            }}
            
            .export-btn {{
                background: linear-gradient(135deg, rgba(76, 175, 80, 0.95), rgba(56, 142, 60, 0.95));
                backdrop-filter: blur(15px);
                color: white;
                border: 2px solid rgba(255,255,255,0.3);
                border-radius: 12px;
                padding: 12px 20px;
                cursor: pointer;
                font-weight: 600;
                font-size: 13px;
                transition: all 0.3s;
                display: flex;
                align-items: center;
                gap: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            }}
            
            .export-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(76,175,80,0.5);
            }}
            
            .export-btn i {{
                font-size: 18px;
            }}
            
            .export-btn.save {{
                background: linear-gradient(135deg, rgba(33, 150, 243, 0.95), rgba(25, 118, 210, 0.95));
            }}
            
            .export-btn.load {{
                background: linear-gradient(135deg, rgba(156, 39, 176, 0.95), rgba(123, 31, 162, 0.95));
            }}
            
            .export-btn:hover.save {{
                box-shadow: 0 6px 20px rgba(33,150,243,0.5);
            }}
            
            .export-btn:hover.load {{
                box-shadow: 0 6px 20px rgba(156,39,176,0.5);
            }}

            #file-input {{
                display: none;
            }}

            /* VIEW NAVIGATION - WITH TOGGLE */
            .nav-panel {{
                position: absolute; top: 20px; right: 20px;
                background: linear-gradient(135deg, rgba(13, 71, 161, 0.95), rgba(25, 118, 210, 0.95));
                backdrop-filter: blur(15px);
                border-radius: 16px;
                padding: 15px;
                border: 2px solid rgba(255,255,255,0.15);
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                touch-action: none;
                transition: all 0.3s;
            }}
            
            .nav-panel.collapsed {{
                padding: 8px;
                width: 50px;
            }}
            
            .nav-toggle-btn {{
                position: absolute;
                top: -10px;
                right: -10px;
                width: 30px;
                height: 30px;
                border-radius: 50%;
                background: linear-gradient(135deg, #2196f3, #1976d2);
                border: 2px solid rgba(255,255,255,0.3);
                color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                z-index: 10;
                transition: all 0.3s;
            }}
            
            .nav-toggle-btn:hover {{
                transform: scale(1.1);
                box-shadow: 0 4px 12px rgba(33,150,243,0.6);
            }}
            
            .nav-content {{
                transition: all 0.3s;
            }}
            
            .nav-content.hidden {{
                display: none;
            }}
            
            .nav-grid {{
                display: grid;
                grid-template-columns: repeat(3, 50px);
                grid-template-rows: repeat(3, 50px);
                gap: 8px;
                margin-bottom: 12px;
            }}
            
            .nav-btn {{
                background: rgba(255,255,255,0.1);
                color: #fff; 
                border: 2px solid rgba(255,255,255,0.2);
                border-radius: 10px; 
                font-size: 11px; 
                font-weight: 600;
                cursor: pointer;
                text-align: center;
                transition: all 0.3s;
                backdrop-filter: blur(10px);
                display: flex;
                align-items: center;
                justify-content: center;
                touch-action: none;
            }}
            
            .nav-btn:hover {{ 
                background: linear-gradient(135deg, #2196f3, #1976d2);
                transform: scale(1.05);
                box-shadow: 0 4px 12px rgba(33,150,243,0.4);
            }}
            
            .nav-btn.center {{
                background: rgba(255,255,255,0.15);
                cursor: default;
                pointer-events: none;
            }}
            
            .rotate-controls {{
                display: grid;
                grid-template-columns: repeat(3, 50px);
                grid-template-rows: repeat(3, 50px);
                gap: 8px;
            }}
            
            .rotate-btn {{
                background: rgba(255,255,255,0.1);
                color: #fff;
                border: 2px solid rgba(255,255,255,0.2);
                border-radius: 10px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s;
                touch-action: none;
            }}
            
            .rotate-btn:hover {{
                background: rgba(255,255,255,0.2);
                transform: scale(1.05);
            }}
            
            .rotate-btn i {{
                font-size: 20px;
            }}
        
            /* TOGGLE SWITCH CSS (FIXED FOR PYTHON F-STRING & LAYOUT) */
            .switch {{
              position: relative;
              display: inline-block;
              width: 40px;
              height: 20px;
            }}
            .switch input {{ 
              opacity: 0; 
              width: 0; 
              height: 0; 
            }}
            /* Đã đổi tên class từ .slider -> .toggle-slider để không trùng */
            .toggle-slider {{
              position: absolute;
              cursor: pointer;
              top: 0; left: 0; right: 0; bottom: 0;
              background-color: rgba(255,255,255,0.2);
              transition: .4s;
              border-radius: 34px;
            }}
            .toggle-slider:before {{
              position: absolute;
              content: "";
              height: 14px;
              width: 14px;
              left: 3px;
              bottom: 3px;
              background-color: white;
              transition: .4s;
              border-radius: 50%;
            }}
            input:checked + .toggle-slider {{
              background-color: #2196F3;
            }}
            input:checked + .toggle-slider:before {{
              transform: translateX(20px);
            }}

        </style>
        
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/OBJLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/MTLLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/tween.js/18.6.4/tween.umd.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    </head>
    <body>
        
        <!-- TOOLBAR -->
        <div class="toolbar">
            <button class="tool-btn active" id="t-view" onclick="selectTool('view')" title="Rotate View">
                <i class="material-icons">3d_rotation</i>
            </button>
            <div class="divider"></div>
            <button class="tool-btn" id="t-brush" onclick="selectTool('brush')" title="Surface Brush">
                <i class="material-icons">brush</i>
            </button>
            <button class="tool-btn" id="t-eraser" onclick="selectTool('eraser')" title="Eraser">
                <i class="material-icons">auto_fix_high</i>
            </button>
            <button class="tool-btn" id="t-line" onclick="selectTool('line')" title="Measurement Line">
                <i class="material-icons">timeline</i>
            </button>
            <button class="tool-btn" id="t-annotation" onclick="selectTool('annotation')" title="Annotation">
                <i class="material-icons">pin_drop</i>
            </button>
            <div class="divider"></div>
            <button class="tool-btn" id="t-distance" onclick="selectTool('distance')" title="Distance Tool">
                <i class="material-icons">straighten</i>
            </button>
            <button class="tool-btn" id="t-angle" onclick="selectTool('angle')" title="Angle Measurement">
                <i class="material-icons">architecture</i>
            </button>
            <div class="divider"></div>
            <button class="tool-btn" id="t-undo" onclick="undo()" title="Undo">
                <i class="material-icons">undo</i>
            </button>
            <button class="tool-btn" id="t-clear" onclick="clearAll()" title="Clear All">
                <i class="material-icons">delete_outline</i>
            </button>
        </div>

        <!-- SETTINGS PANEL -->
       <div class="settings-panel" id="settings">
            <div class="panel-header">
                <span id="tool-name">TOOL SETTINGS</span>
                <button class="close-panel-btn" onclick="toggleSettingsPanel()" title="Hide Settings">×</button>
            </div>
            
            <div>
                <div class="setting-label" style="margin-bottom: 8px;">Surgical Marker Color</div>
                <div class="color-presets">
                    <div class="color-preset active" style="background: #9C27B0;" data-color="#9C27B0" onclick="setColor(this)"></div>
                    <div class="color-preset" style="background: #E91E63;" data-color="#E91E63" onclick="setColor(this)"></div>
                    <div class="color-preset" style="background: #2196F3;" data-color="#2196F3" onclick="setColor(this)"></div>
                    <div class="color-preset" style="background: #4CAF50;" data-color="#4CAF50" onclick="setColor(this)"></div>
                    <div class="color-preset" style="background: #FF9800;" data-color="#FF9800" onclick="setColor(this)"></div>
                    <div class="color-preset" style="background: #F44336;" data-color="#F44336" onclick="setColor(this)"></div>
                    <div class="color-preset" style="background: #00BCD4;" data-color="#00BCD4" onclick="setColor(this)"></div>
                    <div class="color-preset" style="background: #FFEB3B;" data-color="#FFEB3B" onclick="setColor(this)"></div>
                    <div class="color-preset" style="background: #FFFFFF;" data-color="#FFFFFF" onclick="setColor(this)"></div>
                    <div class="color-preset" style="background: #000000;" data-color="#000000" onclick="setColor(this)"></div>
                </div>
            </div>
            
            <div class="setting-row">
                <span class="setting-label">Line Width</span>
                <input type="range" id="p-width" class="slider" min="0.001" max="0.008" step="0.0005" value="0.002" oninput="updateSettings()">
                <span class="value-display" id="width-val">2</span>
            </div>
            
            <div class="setting-row" id="eraser-size-row" style="display:none;">
                <span class="setting-label">Eraser Size</span>
                <input type="range" id="p-eraser" class="slider" min="0.02" max="0.15" step="0.01" value="0.05" oninput="updateSettings()">
                <span class="value-display" id="eraser-val">5</span>
            </div>
            
            <div class="setting-row">
                <span class="setting-label">Opacity</span>
                <input type="range" id="p-opacity" class="slider" min="0.3" max="1" step="0.1" value="0.95" oninput="updateSettings()">
                <span class="value-display" id="opacity-val">0.95</span>
            </div>
            
            <div class="setting-row">
                <span class="setting-label">Surface Offset</span>
                <input type="range" id="p-offset" class="slider" min="0.00001" max="0.001" step="0.00001" value="0.0001" oninput="updateSettings()">
                <span class="value-display" id="offset-val">0.0001</span>
            </div>
            
            <div class="setting-row">
                <span class="setting-label">Auto-Calc Area</span>
                <label class="switch">
                    <input type="checkbox" id="p-auto-area" checked onchange="updateSettings()">
                    <span class="toggle-slider"></span>
                </label>
            </div>
            
            <div id="measure-box" style="display:none;">
                <div class="measurement-box">
                    <div class="measurement-label" id="measure-label">MEASUREMENT</div>
                    <div class="measurement-value" id="measure-value">0.0 mm</div>
                </div>
            </div>
        </div> <div id="info-hud" class="info-hud">Select a tool to start</div>

        <!-- EXPORT PANEL -->
        <div class="export-panel">
            <button class="export-btn" onclick="exportPDFReport()" title="Export PDF Report">
                <i class="material-icons">picture_as_pdf</i>
                <span>Export PDF</span>
            </button>
            <button class="export-btn save" onclick="saveProject()" title="Save Project">
                <i class="material-icons">save</i>
                <span>Save Project</span>
            </button>
            <button class="export-btn load" onclick="document.getElementById('file-input').click()" title="Load Project">
                <i class="material-icons">folder_open</i>
                <span>Load Project</span>
            </button>
        </div>
        
        <input type="file" id="file-input" accept=".json" onchange="loadProject(event)">

        <!-- VIEW NAVIGATION WITH TOGGLE -->
        <div class="nav-panel" id="nav-panel">
            <div class="nav-toggle-btn" onclick="toggleNavPanel()" title="Toggle Navigation Panel">
                <i class="material-icons" id="nav-toggle-icon">remove</i>
            </div>
            
            <div class="nav-content" id="nav-content">
                <div class="nav-grid">
                    <div class="nav-btn" onclick="setView('top')">TOP</div>
                    <div></div>
                    <div></div>
                    
                    <div class="nav-btn" onclick="setView('left')">LEFT</div>
                    <div class="nav-btn center">VIEW</div>
                    <div class="nav-btn" onclick="setView('right')">RIGHT</div>
                    
                    <div></div>
                    <div class="nav-btn" onclick="setView('front')">FRONT</div>
                    <div class="nav-btn" onclick="setView('bottom')">BOT</div>
                </div>
                
                <div style="height: 2px; background: rgba(255,255,255,0.2); margin: 10px 0;"></div>
                
                <div class="rotate-controls">
                    <div></div>
                    <div class="rotate-btn" onclick="rotateCamera('up')">
                        <i class="material-icons">arrow_upward</i>
                    </div>
                    <div></div>
                    
                    <div class="rotate-btn" onclick="rotateCamera('left')">
                        <i class="material-icons">arrow_back</i>
                    </div>
                    <div></div>
                    <div class="rotate-btn" onclick="rotateCamera('right')">
                        <i class="material-icons">arrow_forward</i>
                    </div>
                    
                    <div></div>
                    <div class="rotate-btn" onclick="rotateCamera('down')">
                        <i class="material-icons">arrow_downward</i>
                    </div>
                    <div></div>
                </div>
            </div>
        </div>

        <script>
            let camera, controls, scene, renderer, raycaster, mouse;
            let currentZoom = 300; 
            let targetObject = null;
            let currentTool = 'view';
            const SCALE_FACTOR = {scale_factor};
            
            // Drawing State
            let isDrawing = false;
            let drawPoints = [];
            let tempMeshes = [];
            let drawnObjects = [];
            let lastDrawTime = 0;
            
            // Eraser State
            let isErasing = false;
            let eraserRadius = 0.05;
            let eraserCursor = null;
            
            // Annotation State
            let annotationCounter = 1;
            let annotations = [];
            let draggedAnnotation = null;
            let dragOffset = {{ x: 0, y: 0 }};
            let isDraggingAnnotation = false;
            
            // Measurement State
            let measurePoints = [];
            let measureMarkers = [];
            let floatingLabels = []; // Floating measurement labels
            let measurements = []; // Store all measurements for export
            let draggedLabel = null;
            let labelDragOffset = {{ x: 0, y: 0 }};
            
            // iPad touch handling
            let touchStartTime = 0;
            let longPressTimer = null;
            let lastClickTime = 0; // Prevent double-tap
            
            // UI State
            let settingsPanelVisible = false;
            let navPanelExpanded = true;
            
            // Settings
            let settings = {{
                color: 0x9C27B0,
                colorHex: '#9C27B0',
                lineWidth: 0.002,
                opacity: 0.95,
                offsetFactor: 0.0001,
                autoArea: true
            }};

            function init() {{
                scene = new THREE.Scene();
                scene.background = new THREE.Color(0x1a1a1a);

                camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 2000);
                renderer = new THREE.WebGLRenderer({{ antialias: true, preserveDrawingBuffer: true }});
                renderer.setSize(window.innerWidth, {height});
                renderer.setPixelRatio(window.devicePixelRatio);
                renderer.outputEncoding = THREE.sRGBEncoding;
                document.body.appendChild(renderer.domElement);

                controls = new THREE.OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;
                controls.dampingFactor = 0.05;

                raycaster = new THREE.Raycaster();
                raycaster.params.Line.threshold = 0.5;
                mouse = new THREE.Vector2();

                // LOAD MODEL
                const mtlLoader = new THREE.MTLLoader();
                const materials = mtlLoader.parse(atob("{b64_mtl}"));
                materials.preload();
                
                for (const key in materials.materials) {{
                    const mat = materials.materials[key];
                    const basicMat = new THREE.MeshBasicMaterial({{ 
                        map: mat.map, 
                        side: THREE.DoubleSide 
                    }});
                    if(basicMat.map) basicMat.map.encoding = THREE.sRGBEncoding;
                    materials.materials[key] = basicMat;
                }}

                const objLoader = new THREE.OBJLoader();
                objLoader.setMaterials(materials);
                const object = objLoader.parse(atob("{b64_obj}"));

                const box = new THREE.Box3().setFromObject(object);
                const center = box.getCenter(new THREE.Vector3());
                object.position.sub(center);
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                
                if(maxDim > 0) {{
                     currentZoom = maxDim * 2.0; 
                     camera.position.set(0, 0, currentZoom);
                }} else {{ 
                    camera.position.set(0, 0, 300); 
                }}
                controls.target.set(0, 0, 0);
                
                scene.add(object);
                targetObject = object;

                // Event Listeners - iPad optimized
                const canvas = renderer.domElement;
                
                canvas.addEventListener('contextmenu', (e) => e.preventDefault());
                document.addEventListener('contextmenu', (e) => e.preventDefault());
                
                canvas.addEventListener('touchstart', onTouchStart, {{ passive: false }});
                canvas.addEventListener('touchmove', onTouchMove, {{ passive: false }});
                canvas.addEventListener('touchend', onTouchEnd, {{ passive: false }});
                
                canvas.addEventListener('pointerdown', onDown);
                canvas.addEventListener('pointermove', onMove);
                canvas.addEventListener('pointerup', onUp);
                
                window.addEventListener('resize', () => {{
                    camera.aspect = window.innerWidth / window.innerHeight;
                    camera.updateProjectionMatrix();
                    renderer.setSize(window.innerWidth, {height});
                }});
                
                animate();
                selectTool('view');
            }}

            function animate() {{
                requestAnimationFrame(animate);
                TWEEN.update();
                controls.update();
                renderer.render(scene, camera);
            }}

            // --- iPad TOUCH HANDLING ---
            function onTouchStart(event) {{
                event.preventDefault();
                event.stopPropagation();
                
                touchStartTime = Date.now();
                
                if(longPressTimer) {{
                    clearTimeout(longPressTimer);
                    longPressTimer = null;
                }}
                
                if(event.touches.length === 1 && currentTool !== 'view') {{
                    const touch = event.touches[0];
                    const fakeEvent = {{
                        clientX: touch.clientX,
                        clientY: touch.clientY,
                        button: 0
                    }};
                    onDown(fakeEvent);
                }}
            }}

            function onTouchMove(event) {{
                event.preventDefault();
                event.stopPropagation();
                
                if(longPressTimer) {{
                    clearTimeout(longPressTimer);
                    longPressTimer = null;
                }}
                
                if(event.touches.length === 1 && currentTool !== 'view') {{
                    const touch = event.touches[0];
                    const fakeEvent = {{
                        clientX: touch.clientX,
                        clientY: touch.clientY
                    }};
                    onMove(fakeEvent);
                }}
            }}

            function onTouchEnd(event) {{
                event.preventDefault();
                event.stopPropagation();
                
                if(longPressTimer) {{
                    clearTimeout(longPressTimer);
                    longPressTimer = null;
                }}
                
                const touchDuration = Date.now() - touchStartTime;
                
                if(touchDuration < 500 && currentTool !== 'view') {{
                    const fakeEvent = {{ button: 0 }};
                    onUp(fakeEvent);
                }}
            }}

            // --- TOOL SYSTEM ---
            window.selectTool = function(tool) {{
                if(currentTool === tool && tool !== 'view') {{
                    toggleSettingsPanel();
                    return;
                }}
                
                currentTool = tool;
                resetTemp();
                
                document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
                const btn = document.getElementById('t-' + tool);
                if(btn) btn.classList.add('active');
                
                const sPanel = document.getElementById('settings');
                const tName = document.getElementById('tool-name');
                const hud = document.getElementById('info-hud');
                const measureBox = document.getElementById('measure-box');
                
                measureBox.style.display = 'none';
                
                if (tool === 'view') {{
                    document.body.style.cursor = 'default';
                    controls.enabled = true;
                    sPanel.style.display = 'none';
                    settingsPanelVisible = false;
                    hud.classList.remove('visible');
                }} else {{
                    document.body.style.cursor = 'crosshair';
                    controls.enabled = false;
                    sPanel.style.display = 'flex';
                    settingsPanelVisible = true;
                    hud.classList.add('visible');
                    
                    if(tool === 'brush') {{ 
                        tName.innerText = "SURFACE BRUSH"; 
                        hud.innerText = "Draw closed loop for area measurement"; 
                    }}
                    else if(tool === 'eraser') {{
                        tName.innerText = "ERASER TOOL";
                        hud.innerText = "Click and drag to erase";
                        createEraserCursor();
                    }}
                    else if(tool === 'line') {{ 
                        tName.innerText = "SURGICAL MARKING LINE"; 
                        hud.innerText = "Click two points to draw line"; 
                    }}
                    else if(tool === 'annotation') {{
                        tName.innerText = "ANNOTATION TOOL";
                        hud.innerText = "Click to place numbered marker";
                    }}
                    else if(tool === 'distance') {{ 
                        tName.innerText = "DISTANCE MEASUREMENT"; 
                        hud.innerText = "Click two points to measure";
                        measureBox.style.display = 'block';
                        document.getElementById('measure-label').innerText = "DISTANCE";
                    }}
                    else if(tool === 'angle') {{ 
                        tName.innerText = "ANGLE MEASUREMENT"; 
                        hud.innerText = "Click: A (green) → B (red vertex) → C (blue)";
                        measureBox.style.display = 'block';
                        document.getElementById('measure-label').innerText = "ANGLE";
                    }}
                }}
            }}
            
            window.toggleSettingsPanel = function() {{
                const sPanel = document.getElementById('settings');
                settingsPanelVisible = !settingsPanelVisible;
                sPanel.style.display = settingsPanelVisible ? 'flex' : 'none';
            }}
            
            window.toggleNavPanel = function() {{
                const panel = document.getElementById('nav-panel');
                const content = document.getElementById('nav-content');
                const icon = document.getElementById('nav-toggle-icon');
                
                navPanelExpanded = !navPanelExpanded;
                
                if(navPanelExpanded) {{
                    panel.classList.remove('collapsed');
                    content.classList.remove('hidden');
                    icon.innerText = 'remove';
                }} else {{
                    panel.classList.add('collapsed');
                    content.classList.add('hidden');
                    icon.innerText = 'add';
                }}
            }}

            window.setColor = function(element) {{
                document.querySelectorAll('.color-preset').forEach(e => e.classList.remove('active'));
                element.classList.add('active');
                settings.colorHex = element.dataset.color;
                settings.color = parseInt(element.dataset.color.replace('#', '0x'));
            }}

            window.updateSettings = function() {{
                settings.lineWidth = parseFloat(document.getElementById('p-width').value);
                settings.opacity = parseFloat(document.getElementById('p-opacity').value);
                settings.offsetFactor = parseFloat(document.getElementById('p-offset').value);
                if(document.getElementById('p-auto-area')) {{
                    settings.autoArea = document.getElementById('p-auto-area').checked;
                }}
                
                document.getElementById('width-val').innerText = (settings.lineWidth * 1000).toFixed(1);
                document.getElementById('opacity-val').innerText = settings.opacity.toFixed(2);
                document.getElementById('offset-val').innerText = settings.offsetFactor.toFixed(5);
                
                if(document.getElementById('p-eraser')) {{
                    eraserRadius = parseFloat(document.getElementById('p-eraser').value);
                    document.getElementById('eraser-val').innerText = (eraserRadius * 100).toFixed(0);
                    if(eraserCursor) {{
                        eraserCursor.scale.setScalar(eraserRadius * currentZoom);
                    }}
                }}
            }}

            // --- RAYCASTING ---
            function getIntersects(event) {{
                const rect = renderer.domElement.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                raycaster.setFromCamera(mouse, camera);
                return raycaster.intersectObject(targetObject, true);
            }}

            function getOffsetPoint(hit) {{
                const offset = currentZoom * settings.offsetFactor;
                return hit.point.clone().add(hit.face.normal.clone().multiplyScalar(offset));
            }}

            // --- SURFACE PROJECTION ---
            function projectPointsOnSurface(p1, p2, steps = 20) {{
                const points = [];
                for(let i = 0; i <= steps; i++) {{
                    const t = i / steps;
                    const interpPoint = new THREE.Vector3().lerpVectors(p1, p2, t);
                    
                    const dir = interpPoint.clone().sub(camera.position).normalize();
                    raycaster.set(camera.position, dir);
                    const hits = raycaster.intersectObject(targetObject, true);
                    
                    if(hits.length > 0) {{
                        points.push(getOffsetPoint(hits[0]));
                    }} else {{
                        points.push(interpPoint);
                    }}
                }}
                return points;
            }}

            // --- INTERACTION ---
            function onDown(event) {{
                // Prevent double-tap
                const now = Date.now();
                if (now - lastClickTime < 300) return;
                lastClickTime = now;
                
                if (currentTool === 'view' || event.button !== 0) return;

                const hits = getIntersects(event);
                if (hits.length > 0) {{
                    const point = getOffsetPoint(hits[0]);
                    
                    if (currentTool === 'brush') {{
                        isDrawing = true;
                        drawPoints = [point];
                        lastDrawTime = Date.now();
                    }}
                    else if (currentTool === 'eraser') {{
                        isErasing = true;
                        eraseAtPoint(point);
                    }}
                    else if (currentTool === 'annotation') {{
                        createAnnotation(point, event);
                    }}
                    else if (currentTool === 'line' || currentTool === 'distance') {{
                        if(measurePoints.length === 0) {{
                            measurePoints.push(point);
                            addMarker(point, 0xff0000, false);
                        }} else {{
                            measurePoints.push(point);
                            addMarker(point, 0xff0000, false);
                            
                            if(currentTool === 'line') {{
                                drawSurfaceLine(measurePoints[0], measurePoints[1]);
                            }} else {{
                                measureDistance(measurePoints[0], measurePoints[1]);
                            }}
                            
                            measurePoints = [];
                        }}
                    }}
                    else if (currentTool === 'angle') {{
                        handleAngleMeasurement(point);
                    }}
                }}
            }}

            function onMove(event) {{
                if(currentTool === 'eraser' && eraserCursor) {{
                    const hits = getIntersects(event);
                    if(hits.length > 0) {{
                        eraserCursor.position.copy(getOffsetPoint(hits[0]));
                        eraserCursor.visible = true;
                    }} else {{
                        eraserCursor.visible = false;
                    }}
                }}
                
                if (!isDrawing && !isErasing) return;

                const now = Date.now();
                if(now - lastDrawTime < 16) return;
                lastDrawTime = now;

                const hits = getIntersects(event);
                if (hits.length > 0) {{
                    const point = getOffsetPoint(hits[0]);

                    if (currentTool === 'brush') {{
                        const lastPoint = drawPoints[drawPoints.length - 1];
                        
                        if(point.distanceTo(lastPoint) > currentZoom * 0.001) {{
                            const projected = projectPointsOnSurface(lastPoint, point, 2);
                            drawPoints.push(...projected);
                            updateBrushStroke();
                        }}
                    }}
                    else if (currentTool === 'eraser' && isErasing) {{
                        eraseAtPoint(point);
                    }}
                }}
            }}

            function onUp(event) {{
                if (isDrawing && currentTool === 'brush') {{
                    isDrawing = false;
                    if (drawPoints.length > 10) {{ 
                        const firstPoint = drawPoints[0];
                        const lastPoint = drawPoints[drawPoints.length - 1];
                        const distance = firstPoint.distanceTo(lastPoint);
                        
                        // Ngưỡng khép kín (5% zoom)
                        const closeThreshold = currentZoom * 0.05;

                        if (distance < closeThreshold && settings.autoArea) {{
                            // 1. Nối kín vòng dây
                            drawPoints.push(firstPoint);
                            updateBrushStroke(); 

                            // 2. Tính toán diện tích
                            const areaResult = calculateArea(drawPoints);
                            
                            // 3. Tô màu vùng kín
                            fillClosedLoop(drawPoints, areaResult);
                            
                            // 4. Hiển thị số đo (mm2)
                            const areaText = areaResult.value.toFixed(1) + ' mm²';
                            const labelData = createFloatingLabel(areaResult.center, areaText, 'area');
                            
                            // 5. Lưu vào danh sách (Dùng {{ }} cho object JS)
                            measurements.push({{
                                type: 'area',
                                value: areaResult.value,
                                unit: 'mm²',
                                points: [areaResult.center],
                                labelData: labelData
                            }});
                        }}
                    }}
                    if (tempMeshes.length > 0) {{
                        tempMeshes.forEach(m => drawnObjects.push(m));
                        tempMeshes = [];
                    }}
                    drawPoints = [];
                }}
                
                if (isErasing) {{
                    isErasing = false;
                }}
            }}

            // --- DRAWING TOOLS ---
            function updateBrushStroke() {{
                tempMeshes.forEach(m => scene.remove(m));
                tempMeshes = [];
                
                if(drawPoints.length < 2) return;
                
                const path = new THREE.CatmullRomCurve3(drawPoints);
                const tubeGeo = new THREE.TubeGeometry(path, drawPoints.length * 2, settings.lineWidth * currentZoom, 8, false);
                const tubeMat = new THREE.MeshBasicMaterial({{
                    color: settings.color,
                    transparent: true,
                    opacity: settings.opacity,
                    depthTest: false
                }});
                const tube = new THREE.Mesh(tubeGeo, tubeMat);
                tube.renderOrder = 999;
                scene.add(tube);
                tempMeshes.push(tube);
            }}

            function drawSurfaceLine(p1, p2) {{
                const projected = projectPointsOnSurface(p1, p2, 30);
                
                const path = new THREE.CatmullRomCurve3(projected);
                const tubeGeo = new THREE.TubeGeometry(path, projected.length * 2, settings.lineWidth * currentZoom, 8, false);
                const tubeMat = new THREE.MeshBasicMaterial({{
                    color: settings.color,
                    transparent: true,
                    opacity: settings.opacity,
                    depthTest: false
                }});
                const tube = new THREE.Mesh(tubeGeo, tubeMat);
                tube.renderOrder = 999;
                scene.add(tube);
                drawnObjects.push(tube);
                return tube; // Return for linking to label
            }}

            function addMarker(point, color, isVertex = false) {{
                // Vertex marker lớn hơn để nổi bật
                const size = isVertex ? currentZoom * 0.0035 : currentZoom * 0.002;
                const geo = new THREE.SphereGeometry(size, 16, 16);
                const mat = new THREE.MeshBasicMaterial({{ color: color, depthTest: false }});
                const marker = new THREE.Mesh(geo, mat);
                marker.position.copy(point);
                marker.renderOrder = 1000;
                scene.add(marker);
                measureMarkers.push(marker);
            }}

            // --- ANNOTATION TOOL (FIXED: iPad Touch Support) ---
            function createAnnotation(point3D, event) {{
                // 1. Tạo marker 3D với màu hiện tại
                const markerGeo = new THREE.SphereGeometry(currentZoom * 0.003, 16, 16);
                const markerMat = new THREE.MeshBasicMaterial({{ color: settings.color, depthTest: false }});
                const marker = new THREE.Mesh(markerGeo, markerMat);
                marker.position.copy(point3D);
                marker.renderOrder = 1001;
                scene.add(marker);
                
                // 2. Tạo HTML label
                const label = document.createElement('div');
                label.className = 'annotation-label';
                label.style.background = settings.colorHex;
                
                // Đổi màu chữ nếu nền quá sáng
                if(settings.colorHex === '#FFFFFF' || settings.colorHex === '#FFEB3B') {{
                    label.style.color = '#333';
                }}
                
                const annotId = annotationCounter;
                
                label.innerHTML = `
                    <div class="annotation-header" data-annot-id="${{annotId}}">
                        <div style="display:flex; align-items:center;">
                            <span class="annotation-number" style="background:${{settings.colorHex}}; color:#fff;">${{annotId}}</span>
                            <span style="font-size:11px;">Note #${{annotId}}</span>
                        </div>
                        <i class="material-icons" style="font-size:14px; opacity:0.7;">open_with</i>
                    </div>
                    <div class="annotation-body">
                        <input type="text" 
                               class="annotation-input" 
                               placeholder="Enter note..."
                               onkeydown="event.stopPropagation()"
                               onmousedown="event.stopPropagation()"
                               ontouchstart="event.stopPropagation()">
                    </div>
                `;
                
                document.body.appendChild(label);
                
                const annotation = {{
                    id: annotId,
                    point3D: point3D,
                    marker: marker,
                    label: label,
                    offsetX: 20,
                    offsetY: -40
                }};
                
                annotations.push(annotation);
                drawnObjects.push(marker);
                
                // Setup drag handlers
                setupAnnotationDrag(annotation);
                
                annotationCounter++;
                
                function updateLabelPosition() {{
                    if(!label.parentElement) return;
                    
                    const pos = toScreenPosition(point3D);
                    const finalX = pos.x + annotation.offsetX;
                    const finalY = pos.y + annotation.offsetY;
                    
                    label.style.left = finalX + 'px';
                    label.style.top = finalY + 'px';
                    
                    requestAnimationFrame(updateLabelPosition);
                }}
                updateLabelPosition();
            }}
            
            // --- ANNOTATION DRAGGING (iPad Compatible) ---
            function setupAnnotationDrag(annotation) {{
                const header = annotation.label.querySelector('.annotation-header');
                let dragStartTime = 0;
                
                // Mouse events
                header.addEventListener('mousedown', (e) => {{
                    if(e.target.tagName === 'INPUT') return;
                    e.preventDefault();
                    e.stopPropagation();
                    startAnnotationDrag(annotation, e.clientX, e.clientY);
                }});
                
                // Touch events - iPad optimized
                header.addEventListener('touchstart', (e) => {{
                    dragStartTime = Date.now();
                    e.preventDefault();
                    e.stopPropagation();
                    const touch = e.touches[0];
                    startAnnotationDrag(annotation, touch.clientX, touch.clientY);
                }}, {{ passive: false }});
                
                header.addEventListener('touchend', (e) => {{
                    const dragDuration = Date.now() - dragStartTime;
                    // If very short touch, might be a tap not drag
                    if(dragDuration < 100) {{
                        endAnnotationDrag();
                    }}
                }});
            }}
            
            function startAnnotationDrag(annotation, clientX, clientY) {{
                draggedAnnotation = annotation;
                isDraggingAnnotation = true;
                dragOffset.x = clientX;
                dragOffset.y = clientY;
                annotation.label.style.zIndex = 10000;
                
                // Disable orbit controls when dragging
                if(controls) controls.enabled = false;
            }}
            
            // Global drag handlers
            document.addEventListener('mousemove', (event) => {{
                if (isDraggingAnnotation && draggedAnnotation) {{
                    event.preventDefault();
                    updateAnnotationDrag(event.clientX, event.clientY);
                }}
            }});
            
            document.addEventListener('touchmove', (event) => {{
                if (isDraggingAnnotation && draggedAnnotation) {{
                    event.preventDefault();
                    event.stopPropagation();
                    const touch = event.touches[0];
                    updateAnnotationDrag(touch.clientX, touch.clientY);
                }}
            }}, {{ passive: false }});
            
            document.addEventListener('mouseup', () => {{
                if (isDraggingAnnotation) {{
                    endAnnotationDrag();
                }}
            }});
            
            document.addEventListener('touchend', () => {{
                if (isDraggingAnnotation) {{
                    endAnnotationDrag();
                }}
            }});
            
            function updateAnnotationDrag(clientX, clientY) {{
                const deltaX = clientX - dragOffset.x;
                const deltaY = clientY - dragOffset.y;
                
                draggedAnnotation.offsetX += deltaX;
                draggedAnnotation.offsetY += deltaY;
                
                dragOffset.x = clientX;
                dragOffset.y = clientY;
            }}
            
            function endAnnotationDrag() {{
                isDraggingAnnotation = false;
                if(draggedAnnotation) {{
                    draggedAnnotation.label.style.zIndex = 1000;
                    draggedAnnotation = null;
                }}
                // Re-enable orbit controls if in view mode
                if(controls && currentTool === 'view') {{
                    controls.enabled = true;
                }}
            }}

            // --- ERASER TOOL ---
            function createEraserCursor() {{
                if(eraserCursor) {{
                    scene.remove(eraserCursor);
                }}
                
                const geo = new THREE.SphereGeometry(1, 32, 32);
                const mat = new THREE.MeshBasicMaterial({{
                    color: 0xff5252,
                    transparent: true,
                    opacity: 0.3,
                    depthTest: false,
                    wireframe: true
                }});
                eraserCursor = new THREE.Mesh(geo, mat);
                eraserCursor.scale.setScalar(eraserRadius * currentZoom);
                eraserCursor.renderOrder = 2000;
                eraserCursor.visible = false;
                scene.add(eraserCursor);
                
                document.getElementById('eraser-size-row').style.display = 'flex';
            }}
            
            function eraseAtPoint(point) {{
                const eraseRadiusWorld = eraserRadius * currentZoom;
                
                // Check drawn objects
                for(let i = drawnObjects.length - 1; i >= 0; i--) {{
                    const obj = drawnObjects[i];
                    
                    if(obj.geometry && obj.geometry.attributes && obj.geometry.attributes.position) {{
                        const positions = obj.geometry.attributes.position.array;
                        let shouldErase = false;
                        
                        for(let j = 0; j < positions.length; j += 3) {{
                            const vertex = new THREE.Vector3(
                                positions[j],
                                positions[j + 1],
                                positions[j + 2]
                            );
                            
                            vertex.applyMatrix4(obj.matrixWorld);
                            
                            if(vertex.distanceTo(point) < eraseRadiusWorld) {{
                                shouldErase = true;
                                break;
                            }}
                        }}
                        
                        if(shouldErase) {{
                            // Check if this object is linked to a label
                            const linkedLabel = floatingLabels.find(l => 
                                l.relatedObjects.includes(obj)
                            );
                            
                            if(linkedLabel) {{
                                // Delete entire measurement including label
                                deleteFloatingLabel(linkedLabel);
                            }} else {{
                                // Just delete the object
                                scene.remove(obj);
                                if(obj.geometry) obj.geometry.dispose();
                                if(obj.material) obj.material.dispose();
                                drawnObjects.splice(i, 1);
                            }}
                        }}
                    }}
                    else if(obj.type === 'Mesh' && obj.geometry && obj.geometry.type === 'SphereGeometry') {{
                        if(obj.position.distanceTo(point) < eraseRadiusWorld) {{
                            scene.remove(obj);
                            if(obj.geometry) obj.geometry.dispose();
                            if(obj.material) obj.material.dispose();
                            
                            const annotation = annotations.find(a => a.marker === obj);
                            if(annotation) {{
                                annotation.label.remove();
                                annotations = annotations.filter(a => a !== annotation);
                            }}
                            
                            drawnObjects.splice(i, 1);
                        }}
                    }}
                }}
            }}

            function toScreenPosition(point3D) {{
                const vector = point3D.clone();
                vector.project(camera);
                
                const rect = renderer.domElement.getBoundingClientRect();
                return {{
                    x: (vector.x + 1) / 2 * rect.width + rect.left,
                    y: -(vector.y - 1) / 2 * rect.height + rect.top
                }};
            }}
            
            // --- FLOATING LABELS (DRAGGABLE & DELETABLE) ---
            function createFloatingLabel(point3D, text, type) {{
                const label = document.createElement('div');
                label.className = `floating-label ${{type}}`;
                
                const textSpan = document.createElement('span');
                textSpan.innerText = text;
                
                const closeBtn = document.createElement('button');
                closeBtn.className = 'label-close-btn';
                closeBtn.innerHTML = '×';
                closeBtn.title = 'Delete measurement';
                
                label.appendChild(textSpan);
                label.appendChild(closeBtn);
                
                document.body.appendChild(label);
                
                const labelData = {{
                    element: label,
                    point3D: point3D.clone(),
                    text: text,
                    type: type,
                    offsetX: 0,
                    offsetY: -30,
                    relatedObjects: [] // Store related line/mesh objects
                }};
                
                floatingLabels.push(labelData);
                
                // 1. Mouse (Máy tính)
                label.addEventListener('mousedown', (e) => {{
                    if(e.target === closeBtn) return;
                    e.preventDefault();
                    e.stopPropagation();
                    draggedLabel = labelData;
                    labelDragOffset.x = e.clientX - parseFloat(label.style.left);
                    labelDragOffset.y = e.clientY - parseFloat(label.style.top);
                }});

                // 2. Touch (iPad/Điện thoại) - ĐANG THIẾU CÁI NÀY
                label.addEventListener('touchstart', (e) => {{
                    if(e.target === closeBtn) return;
                    e.preventDefault();
                    e.stopPropagation();
                    const touch = e.touches[0];
                    draggedLabel = labelData;
                    // Lấy vị trí hiện tại của nhãn
                    const currentLeft = parseFloat(label.style.left) || 0;
                    const currentTop = parseFloat(label.style.top) || 0;
                    labelDragOffset.x = touch.clientX - currentLeft;
                    labelDragOffset.y = touch.clientY - currentTop;
                }}, {{ passive: false }});
                
                // Delete functionality
                const handleDelete = (e) => {{
                    e.preventDefault();
                    e.stopPropagation(); // Chặn ngay lập tức, không cho sự kiện lan xuống nhãn
                    deleteFloatingLabel(labelData);
                    draggedLabel = null; // Ngắt trạng thái kéo nếu có lỡ kích hoạt
                }};

                closeBtn.addEventListener('click', handleDelete);
                // QUAN TRỌNG: Thêm touchstart để iPad nhận diện ngay lập tức
                closeBtn.addEventListener('touchstart', handleDelete, {{ passive: false }});
                
                function updatePosition() {{
                    if(!label.parentElement) return;
                    const pos = toScreenPosition(point3D);
                    label.style.left = (pos.x + labelData.offsetX) + 'px';
                    label.style.top = (pos.y + labelData.offsetY) + 'px';
                    requestAnimationFrame(updatePosition);
                }}
                updatePosition();
                
                return labelData;
            }}
            
           // --- GLOBAL DRAG HANDLERS (UPDATED: ANTI-STICKY LOGIC) ---
            
            // 1. Xử lý di chuyển cho LABEL (Floating Label)
            function handleLabelMove(clientX, clientY, event) {{
                if(draggedLabel) {{
                    event.preventDefault();
                    event.stopPropagation();
                    
                    const newX = clientX - labelDragOffset.x;
                    const newY = clientY - labelDragOffset.y;
                    
                    draggedLabel.element.style.left = newX + 'px';
                    draggedLabel.element.style.top = newY + 'px';
                    
                    // Cập nhật offset tương đối để xoay 3D vẫn chuẩn
                    const originalPos = toScreenPosition(draggedLabel.point3D);
                    draggedLabel.offsetX = newX - originalPos.x;
                    draggedLabel.offsetY = newY - originalPos.y;
                }}
            }}

            // Sự kiện chuột
            document.addEventListener('mousemove', (e) => {{
                handleLabelMove(e.clientX, e.clientY, e);
            }});
            
            // Sự kiện cảm ứng (iPad) - Thêm passive: false để chặn cuộn trang
            document.addEventListener('touchmove', (e) => {{
                if(draggedLabel) {{
                    const touch = e.touches[0];
                    handleLabelMove(touch.clientX, touch.clientY, e);
                }}
            }}, {{ passive: false }});

            // 2. Xử lý thả tay (End/Drop) - GLOBAL KILL SWITCH
            // Hàm này sẽ ngắt mọi loại kéo thả (cả Label lẫn Annotation)
            function endAllDrags() {{
                // Ngắt Label
                draggedLabel = null;
                
                // Ngắt Annotation (nếu đang bị dính)
                if (typeof isDraggingAnnotation !== 'undefined' && isDraggingAnnotation) {{
                    isDraggingAnnotation = false;
                    
                    // Reset lại style cho Annotation
                    if(draggedAnnotation) {{
                        draggedAnnotation.label.style.zIndex = 1000;
                        draggedAnnotation = null;
                    }}
                    
                    // Trả lại quyền xoay 3D cho OrbitControls
                    if(controls && currentTool === 'view') {{
                        controls.enabled = true;
                    }}
                }}
            }}

            // Bắt sự kiện trên toàn bộ cửa sổ (Window) để không bị sót
            window.addEventListener('mouseup', endAllDrags);
            window.addEventListener('touchend', endAllDrags);
            window.addEventListener('touchcancel', endAllDrags); // Quan trọng: Xử lý khi có noti/cuộc gọi làm ngắt touch
            window.addEventListener('blur', endAllDrags);        // Xử lý khi tab bị ẩn hoặc switch app
            
            function deleteFloatingLabel(labelData) {{
                // Remove label element
                if(labelData.element && labelData.element.parentElement) {{
                    labelData.element.remove();
                }}
                
                // Remove related 3D objects (lines, meshes)
                labelData.relatedObjects.forEach(obj => {{
                    scene.remove(obj);
                    if(obj.geometry) obj.geometry.dispose();
                    if(obj.material) obj.material.dispose();
                    
                    const index = drawnObjects.indexOf(obj);
                    if(index > -1) drawnObjects.splice(index, 1);
                }});
                
                // Remove from floatingLabels array
                const index = floatingLabels.indexOf(labelData);
                if(index > -1) floatingLabels.splice(index, 1);
                
                // Remove from measurements array
                const measureIndex = measurements.findIndex(m => 
                    m.labelData === labelData
                );
                if(measureIndex > -1) measurements.splice(measureIndex, 1);
            }}
            
            // --- AREA CALCULATION (SKIN FLAP) ---
            function calculateArea(points3D) {{
                if (points3D.length < 3) return {{ value: 0, center: new THREE.Vector3() }};
                
                // 1. Tính vector pháp tuyến và tâm (Newell's method)
                let normal = new THREE.Vector3();
                let center = new THREE.Vector3();
                
                for (let i = 0; i < points3D.length; i++) {{
                    let j = (i + 1) % points3D.length;
                    normal.x += (points3D[i].y - points3D[j].y) * (points3D[i].z + points3D[j].z);
                    normal.y += (points3D[i].z - points3D[j].z) * (points3D[i].x + points3D[j].x);
                    normal.z += (points3D[i].x - points3D[j].x) * (points3D[i].y + points3D[j].y);
                    center.add(points3D[i]);
                }}
                normal.normalize();
                center.divideScalar(points3D.length);
                
                // 2. Tạo Quaternion để xoay về mặt phẳng XY
                const alignVector = new THREE.Vector3(0, 0, 1);
                const quaternion = new THREE.Quaternion().setFromUnitVectors(normal, alignVector);
                
                // 3. Chiếu điểm sang 2D
                const points2D = points3D.map(p => {{
                    const vec = p.clone().sub(center).applyQuaternion(quaternion);
                    return new THREE.Vector2(vec.x, vec.y);
                }});
                
                // 4. Tính diện tích 2D (Shoelace formula)
                const areaVirtual = THREE.ShapeUtils.area(points2D);
                
                // 5. Đổi sang mm² thật
                const areaReal = Math.abs(areaVirtual) * SCALE_FACTOR * SCALE_FACTOR;
                
                return {{
                    value: areaReal,
                    points2D: points2D,
                    center: center,
                    quaternion: quaternion
                }};
            }}
            
            // Tô màu vùng đã chọn (Tạo Flap Mesh)
            function fillClosedLoop(points3D, areaData) {{
                const shape = new THREE.Shape(areaData.points2D);
                const geometry = new THREE.ShapeGeometry(shape);
                
                const material = new THREE.MeshBasicMaterial({{
                    color: settings.color,
                    transparent: true,
                    opacity: 0.4,
                    side: THREE.DoubleSide,
                    depthTest: false
                }});
                
                const mesh = new THREE.Mesh(geometry, material);
                
                // Xoay về vị trí 3D ban đầu
                const invertQuat = areaData.quaternion.clone().invert();
                mesh.quaternion.copy(invertQuat);
                mesh.position.copy(areaData.center);
                
                // Đẩy nhẹ lên bề mặt
                const offsetVec = new THREE.Vector3(0, 0, currentZoom * 0.001);
                offsetVec.applyQuaternion(invertQuat);
                mesh.position.add(offsetVec);
                
                mesh.renderOrder = 998;
                scene.add(mesh);
                drawnObjects.push(mesh);
                
                return mesh;
            }}

            function measureDistance(p1, p2) {{
                const dist = p1.distanceTo(p2) * SCALE_FACTOR;
                const distText = dist.toFixed(2) + ' mm';
                document.getElementById('measure-value').innerText = distText;
                
                const line = drawSurfaceLine(p1, p2);
                
                // Tạo floating label
                const midPoint = new THREE.Vector3().lerpVectors(p1, p2, 0.5);
                const labelData = createFloatingLabel(midPoint, distText, 'distance');
                labelData.relatedObjects = [line]; // Link line to label
                
                // Lưu vào measurements
                measurements.push({{
                    type: 'distance',
                    value: dist,
                    unit: 'mm',
                    points: [p1.clone(), p2.clone()],
                    labelData: labelData
                }});
                
                setTimeout(() => {{
                    measureMarkers.forEach(m => scene.remove(m));
                    measureMarkers = [];
                }}, 3000);
            }}

            // --- ANGLE MEASUREMENT (CORRECTED: A-B-C LOGIC) ---
            // --- ANGLE MEASUREMENT (FIXED FOR PYTHON F-STRING) ---
            function handleAngleMeasurement(point) {{
                // 1. Tự động Reset: Nếu đã đo xong 3 điểm, chạm tiếp sẽ bắt đầu góc mới
                if (measurePoints.length === 3) {{
                    measureMarkers.forEach(m => scene.remove(m));
                    measureMarkers = [];
                    measurePoints = [];
                    // Xóa đường line tạm cũ
                     if(window.tempAngleLines) {{
                        window.tempAngleLines.forEach(l => scene.remove(l));
                        window.tempAngleLines = [];
                    }}
                    document.getElementById('measure-value').innerText = "0.0°";
                    document.getElementById('info-hud').innerText = "Starting new angle...";
                }}

                // 2. CHỐNG TRÙNG ĐIỂM (QUAN TRỌNG CHO iPAD)
                if (measurePoints.length > 0) {{
                    const lastPoint = measurePoints[measurePoints.length - 1];
                    const dist = point.distanceTo(lastPoint);
                    // Ngưỡng lọc: khoảng 1% độ zoom hiện tại
                    if (dist < currentZoom * 0.01) {{ 
                        console.log("Ignored double tap");
                        return; 
                    }}
                }}

                measurePoints.push(point);
                
                // --- Logic hiển thị màu và tính toán ---
                let markerColor;
                let isVertex = false;
                
                if(measurePoints.length === 1) {{
                    markerColor = 0x4CAF50; // A - Xanh lá
                    document.getElementById('info-hud').innerText = "Point A set. Click Vertex B (Đỉnh góc)";
                }}
                else if(measurePoints.length === 2) {{
                    markerColor = 0xFF0000; // B - Đỏ
                    isVertex = true;
                    document.getElementById('info-hud').innerText = "Vertex B set. Click Point C";
                    
                    // Vẽ cạnh BA
                    const line1 = drawSurfaceLine(measurePoints[1], measurePoints[0]);
                    if(!window.tempAngleLines) window.tempAngleLines = [];
                    window.tempAngleLines.push(line1);
                }}
                else if(measurePoints.length === 3) {{
                    markerColor = 0x2196F3; // C - Xanh dương
                    
                    const pointA = measurePoints[0];
                    const pointB = measurePoints[1];
                    const pointC = measurePoints[2];
                    
                    const vectorBA = pointA.clone().sub(pointB).normalize();
                    const vectorBC = pointC.clone().sub(pointB).normalize();
                    
                    const angleRad = vectorBA.angleTo(vectorBC);
                    const angleDeg = THREE.MathUtils.radToDeg(angleRad);
                    const angleText = angleDeg.toFixed(1) + '°';
                    
                    document.getElementById('measure-value').innerText = angleText;
                    // Chú ý: Dùng ${{ }} cho biến JS trong chuỗi
                    document.getElementById('info-hud').innerText = `∠ABC = ${{angleText}} (Click to start new)`;
                    
                    // Vẽ cạnh BC
                    const line2 = drawSurfaceLine(measurePoints[1], measurePoints[2]);
                    if(!window.tempAngleLines) window.tempAngleLines = [];
                    window.tempAngleLines.push(line2);
                    
                    // Tạo nhãn kết quả
                    const labelData = createFloatingLabel(pointB, '∠' + angleText, 'angle');
                    labelData.relatedObjects = [...window.tempAngleLines];
                    
                    // Lưu vào báo cáo
                    measurements.push({{
                        type: 'angle',
                        value: angleDeg,
                        unit: '°',
                        points: [pointA.clone(), pointB.clone(), pointC.clone()],
                        labelData: labelData
                    }});

                    window.tempAngleLines = [];
                }}
                
                addMarker(point, markerColor, isVertex);
            }}

            // --- EXPORT PDF REPORT ---
            window.exportPDFReport = async function() {{
                const {{ jsPDF }} = window.jspdf;
                const pdf = new jsPDF('p', 'mm', 'a4');
                
                // Hide UI elements temporarily
                document.querySelector('.toolbar').style.display = 'none';
                document.querySelector('.settings-panel').style.display = 'none';
                document.querySelector('.nav-panel').style.display = 'none';
                document.querySelector('.export-panel').style.display = 'none';
                document.querySelector('.info-hud').style.display = 'none';
                
                const captureView = async (viewName) => {{
                    return new Promise((resolve) => {{
                        setView(viewName);
                        setTimeout(async () => {{
                            const canvas = await html2canvas(document.body, {{
                                backgroundColor: '#1a1a1a',
                                scale: 1
                            }});
                            resolve(canvas.toDataURL('image/jpeg', 0.8));
                        }}, 1000);
                    }});
                }};
                
                // Capture 3 views
                const frontImg = await captureView('front');
                const leftImg = await captureView('left');
                const rightImg = await captureView('right');
                
                // Restore UI
                document.querySelector('.toolbar').style.display = 'flex';
                document.querySelector('.nav-panel').style.display = 'block';
                document.querySelector('.export-panel').style.display = 'flex';
                
                // Build PDF
                const pageWidth = 210;
                const pageHeight = 297;
                const margin = 15;
                const imgWidth = (pageWidth - 3 * margin) / 2;
                const imgHeight = imgWidth * 0.75;
                
                // Header
                pdf.setFontSize(20);
                pdf.setTextColor(33, 150, 243);
                pdf.text('HIDU Surgical Planning Report', margin, margin + 10);
                
                pdf.setFontSize(10);
                pdf.setTextColor(100);
                const date = new Date().toLocaleDateString();
                pdf.text(`Date: ${{date}}`, margin, margin + 18);
                
                // Images
                let y = margin + 30;
                pdf.setFontSize(12);
                pdf.setTextColor(0);
                
                pdf.text('Front View', margin, y);
                pdf.addImage(frontImg, 'JPEG', margin, y + 5, imgWidth, imgHeight);
                
                pdf.text('Left Profile', pageWidth - margin - imgWidth, y);
                pdf.addImage(leftImg, 'JPEG', pageWidth - margin - imgWidth, y + 5, imgWidth, imgHeight);
                
                y += imgHeight + 15;
                pdf.text('Right Profile', margin, y);
                pdf.addImage(rightImg, 'JPEG', margin, y + 5, imgWidth, imgHeight);
                
                // Measurements Table
                y += imgHeight + 20;
                if(measurements.length > 0) {{
                    pdf.setFontSize(14);
                    pdf.setTextColor(33, 150, 243);
                    pdf.text('Measurements', margin, y);
                    y += 8;
                    
                    pdf.setFontSize(10);
                    pdf.setTextColor(0);
                    
                    // Group by type
                    const distances = measurements.filter(m => m.type === 'distance');
                    const angles = measurements.filter(m => m.type === 'angle');
                    const areas = measurements.filter(m => m.type === 'area');
                    
                    if(distances.length > 0) {{
                        pdf.setTextColor(33, 150, 243);
                        pdf.text('Distances:', margin + 2, y);
                        y += 5;
                        pdf.setTextColor(0);
                        distances.forEach((m, i) => {{
                            const text = `  • ${{m.value.toFixed(2)}} mm`;
                            pdf.text(text, margin + 5, y);
                            y += 5;
                        }});
                        y += 2;
                    }}
                    
                    if(angles.length > 0) {{
                        pdf.setTextColor(255, 152, 0);
                        pdf.text('Angles:', margin + 2, y);
                        y += 5;
                        pdf.setTextColor(0);
                        angles.forEach((m, i) => {{
                            const text = `  • ${{m.value.toFixed(1)}}°`;
                            pdf.text(text, margin + 5, y);
                            y += 5;
                        }});
                        y += 2;
                    }}
                    
                    if(areas.length > 0) {{
                        pdf.setTextColor(156, 39, 176);
                        pdf.text('Skin Flap Areas:', margin + 2, y);
                        y += 5;
                        pdf.setTextColor(0);
                        areas.forEach((m, i) => {{
                            const text = `  • ${{m.value.toFixed(1)}} mm² (Flap ${{i + 1}})`;
                            pdf.text(text, margin + 5, y);
                            y += 5;
                        }});
                    }}
                }}
                
                // Annotations
                if(annotations.length > 0) {{
                    y += 5;
                    pdf.setFontSize(14);
                    pdf.setTextColor(33, 150, 243);
                    pdf.text('Annotations', margin, y);
                    y += 8;
                    
                    pdf.setFontSize(10);
                    pdf.setTextColor(0);
                    
                    annotations.forEach((a, i) => {{
                        const input = a.label.querySelector('.annotation-input');
                        const note = input ? input.value || '(No note)' : '(No note)';
                        pdf.text(`${{i + 1}}. ${{note}}`, margin + 5, y);
                        y += 6;
                    }});
                }}
                
                // Footer
                pdf.setFontSize(8);
                pdf.setTextColor(150);
                pdf.text('Generated by HIDU Surgical Planning Studio', margin, pageHeight - 10);
                
                // Save
                pdf.save(`surgical-plan-${{date.replace(/\\//g, '-')}}.pdf`);
                
                alert('PDF exported successfully!');
            }};
            
            // --- SAVE PROJECT ---
            window.saveProject = function() {{
                const projectData = {{
                    version: '1.0',
                    date: new Date().toISOString(),
                    scaleFactor: SCALE_FACTOR,
                    drawnObjects: [],
                    annotations: [],
                    measurements: measurements
                }};
                
                // Serialize drawn objects
                drawnObjects.forEach(obj => {{
                    if(obj.geometry && obj.geometry.attributes && obj.geometry.attributes.position) {{
                        const positions = Array.from(obj.geometry.attributes.position.array);
                        projectData.drawnObjects.push({{
                            type: obj.geometry.type,
                            positions: positions,
                            color: obj.material.color.getHex(),
                            opacity: obj.material.opacity
                        }});
                    }}
                }});
                
                // Serialize annotations
                annotations.forEach(a => {{
                    const input = a.label.querySelector('.annotation-input');
                    projectData.annotations.push({{
                        id: a.id,
                        point3D: {{x: a.point3D.x, y: a.point3D.y, z: a.point3D.z}},
                        offsetX: a.offsetX,
                        offsetY: a.offsetY,
                        text: input ? input.value : '',
                        color: a.marker.material.color.getHex()
                    }});
                }});
                
                // Download JSON
                const blob = new Blob([JSON.stringify(projectData, null, 2)], {{ type: 'application/json' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `surgical-plan-${{new Date().toISOString().split('T')[0]}}.json`;
                a.click();
                URL.revokeObjectURL(url);
                
                alert('Project saved successfully!');
            }};
            
            // --- LOAD PROJECT ---
            window.loadProject = function(event) {{
                const file = event.target.files[0];
                if(!file) return;
                
                const reader = new FileReader();
                reader.onload = function(e) {{
                    try {{
                        const projectData = JSON.parse(e.target.result);
                        
                        // Clear current scene
                        clearAll();
                        
                        // Restore drawn objects
                        projectData.drawnObjects.forEach(objData => {{
                            const positions = new Float32Array(objData.positions);
                            const geometry = new THREE.BufferGeometry();
                            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
                            
                            const material = new THREE.MeshBasicMaterial({{
                                color: objData.color,
                                transparent: true,
                                opacity: objData.opacity,
                                depthTest: false
                            }});
                            
                            let mesh;
                            if(objData.type === 'TubeGeometry') {{
                                mesh = new THREE.Mesh(geometry, material);
                            }} else {{
                                mesh = new THREE.Line(geometry, material);
                            }}
                            
                            mesh.renderOrder = 999;
                            scene.add(mesh);
                            drawnObjects.push(mesh);
                        }});
                        
                        // Restore annotations
                        projectData.annotations.forEach(aData => {{
                            const point3D = new THREE.Vector3(aData.point3D.x, aData.point3D.y, aData.point3D.z);
                            
                            // Create marker
                            const markerGeo = new THREE.SphereGeometry(currentZoom * 0.003, 16, 16);
                            const markerMat = new THREE.MeshBasicMaterial({{ color: aData.color, depthTest: false }});
                            const marker = new THREE.Mesh(markerGeo, markerMat);
                            marker.position.copy(point3D);
                            marker.renderOrder = 1001;
                            scene.add(marker);
                            
                            // Create label
                            const label = document.createElement('div');
                            label.className = 'annotation-label';
                            label.style.background = '#' + aData.color.toString(16).padStart(6, '0');
                            
                            label.innerHTML = `
                                <div class="annotation-header" onmousedown="startDragAnnotation(event, ${{aData.id}})">
                                    <div style="display:flex; align-items:center;">
                                        <span class="annotation-number" style="background:#${{aData.color.toString(16).padStart(6, '0')}}; color:#fff;">${{aData.id}}</span>
                                        <span style="font-size:11px;">Note #${{aData.id}}</span>
                                    </div>
                                    <i class="material-icons" style="font-size:14px; opacity:0.7;">open_with</i>
                                </div>
                                <div class="annotation-body">
                                    <input type="text" 
                                           class="annotation-input" 
                                           placeholder="Enter note..."
                                           value="${{aData.text}}"
                                           onkeydown="event.stopPropagation()"
                                           onmousedown="event.stopPropagation()">
                                </div>
                            `;
                            
                            document.body.appendChild(label);
                            
                            const annotation = {{
                                id: aData.id,
                                point3D: point3D,
                                marker: marker,
                                label: label,
                                offsetX: aData.offsetX,
                                offsetY: aData.offsetY
                            }};
                            
                            annotations.push(annotation);
                            drawnObjects.push(marker);
                            
                            if(aData.id >= annotationCounter) {{
                                annotationCounter = aData.id + 1;
                            }}
                            
                            function updatePos() {{
                                if(!label.parentElement) return;
                                const pos = toScreenPosition(point3D);
                                label.style.left = (pos.x + annotation.offsetX) + 'px';
                                label.style.top = (pos.y + annotation.offsetY) + 'px';
                                requestAnimationFrame(updatePos);
                            }}
                            updatePos();
                        }});
                        
                        // Restore measurements
                        if(projectData.measurements) {{
                            measurements = projectData.measurements;
                        }}
                        
                        alert('Project loaded successfully!');
                    }} catch(error) {{
                        alert('Error loading project: ' + error.message);
                    }}
                }};
                reader.readAsText(file);
            }};
            
            // --- UTILITIES ---
            window.undo = function() {{
                if (drawnObjects.length > 0) {{
                    const obj = drawnObjects.pop();
                    scene.remove(obj);
                    if(obj.geometry) obj.geometry.dispose();
                    if(obj.material) obj.material.dispose();
                    
                    const annotation = annotations.find(a => a.marker === obj);
                    if(annotation) {{
                        annotation.label.remove();
                        annotations = annotations.filter(a => a !== annotation);
                    }}
                }}
            }}

            window.clearAll = function() {{
                if(confirm('Clear all surgical markings and annotations?')) {{
                    while(drawnObjects.length > 0) undo();
                    resetTemp();
                    annotationCounter = 1;
                    measurements = [];
                    
                    // Remove floating labels
                    floatingLabels.forEach(l => {{
                        if(l.element && l.element.parentElement) {{
                            l.element.remove();
                        }}
                    }});
                    floatingLabels = [];
                }}
            }}

            function resetTemp() {{
                tempMeshes.forEach(m => {{
                    scene.remove(m);
                    if(m.geometry) m.geometry.dispose();
                    if(m.material) m.material.dispose();
                }});
                tempMeshes = [];
                
                measurePoints = [];
                measureMarkers.forEach(m => scene.remove(m));
                measureMarkers = [];
                drawPoints = [];
                isDrawing = false;
                isErasing = false;
                
                if(eraserCursor) {{
                    eraserCursor.visible = false;
                }}
                document.getElementById('eraser-size-row').style.display = 'none';
            }}

            // --- VIEW CONTROLS ---
            window.setView = function(v) {{
                const d = currentZoom * 0.8;
                const views = {{
                    'front': {{p: {{x:0, y:0, z:d}}, u: {{x:0, y:1, z:0}}}},
                    'left': {{p: {{x:-d, y:0, z:0}}, u: {{x:0, y:1, z:0}}}},
                    'right': {{p: {{x:d, y:0, z:0}}, u: {{x:0, y:1, z:0}}}},
                    'top': {{p: {{x:0, y:d, z:0}}, u: {{x:0, y:0, z:-1}}}},
                    'bottom': {{p: {{x:0, y:-d, z:0}}, u: {{x:0, y:0, z:1}}}}
                }};
                
                const target = views[v];
                if(!target) return;
                
                new TWEEN.Tween(controls.target)
                    .to({{x:0, y:0, z:0}}, 600)
                    .easing(TWEEN.Easing.Cubic.InOut)
                    .start();
                    
                new TWEEN.Tween(camera.position)
                    .to(target.p, 800)
                    .easing(TWEEN.Easing.Cubic.InOut)
                    .onUpdate(() => {{
                        camera.up.copy(target.u);
                    }})
                    .start();
            }}

            window.rotateCamera = function(direction) {{
                const rotateAmount = Math.PI / 8;
                const currentPos = camera.position.clone();
                const target = controls.target.clone();
                
                let newPos = currentPos.clone().sub(target);
                
                if(direction === 'left') {{
                    const axis = new THREE.Vector3(0, 1, 0);
                    newPos.applyAxisAngle(axis, rotateAmount);
                }}
                else if(direction === 'right') {{
                    const axis = new THREE.Vector3(0, 1, 0);
                    newPos.applyAxisAngle(axis, -rotateAmount);
                }}
                else if(direction === 'up') {{
                    const axis = new THREE.Vector3(1, 0, 0);
                    newPos.applyAxisAngle(axis, rotateAmount);
                }}
                else if(direction === 'down') {{
                    const axis = new THREE.Vector3(1, 0, 0);
                    newPos.applyAxisAngle(axis, -rotateAmount);
                }}
                
                newPos.add(target);
                
                new TWEEN.Tween(camera.position)
                    .to({{x: newPos.x, y: newPos.y, z: newPos.z}}, 400)
                    .easing(TWEEN.Easing.Cubic.Out)
                    .start();
            }}

            init();
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=height)

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Model Input")
    st.markdown("Upload 3D scan from Scaniverse")
    uploaded_file = st.file_uploader("", type="zip", label_visibility="collapsed")
    
    st.divider()
    
    st.header("📏 Calibration")
    st.markdown("*Calibrate measurements using known distance*")
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Virtual (units)", key="v_dist", format="%.2f", help="Measured distance on 3D model")
    with col2:
        st.number_input("Real (mm)", value=20.0, key="r_dist", help="Actual physical distance")
    
    if st.button("⚡ Apply Calibration", use_container_width=True):
        v = st.session_state.v_dist
        if v > 0:
            s = st.session_state.r_dist / v
            st.session_state['scale_factor'] = s
            st.success(f"✓ Scale factor: {s:.4f}")
        else:
            st.error("Virtual distance must be > 0")
    
    st.divider()
    
    st.markdown("### 🎯 Feature Guide")
    st.markdown("""
    **Drawing Tools:**
    - 🖱️ **View**: Rotate and zoom
    - 🖌️ **Brush**: Freehand drawing (adjustable width)
    - 🧹 **Eraser**: Remove markings
    - 📏 **Line**: Straight surgical lines
    - 📍 **Annotation**: Colored markers with notes
    
    **Measurement Guide:**
    - 📐 **Distance**: Click 2 points (red markers)
    - 📊 **Angle**: 3-step process
      1. Click **Point A** (green marker)
      2. Click **Vertex B** (red marker - angle vertex)
      3. Click **Point C** (blue marker)
      - Result: Angle ∠ABC at vertex B
      - Both edges BA and BC are drawn
    
    **UI Controls:**
    - Click tool twice to toggle settings panel
    - Click "−" button to collapse navigation panel
    - Drag annotation headers to reposition
    - Annotations inherit selected color
    
    **Line Width:**
    - Range: 1-8 (thinner options available)
    - Adjustable in real-time
    """)

# --- MAIN AREA ---
if uploaded_file:
    st.cache_data.clear()
    with st.spinner("🔄 Loading surgical planning studio..."):
        obj, mtl, err = process_file_high_quality(uploaded_file)
    
    if err:
        st.error(err)
    else:
        render_studio_viewer(obj, mtl, st.session_state['scale_factor'], height=750)
else:
    st.info("👆 Upload a Scaniverse .zip file to begin surgical planning")
    st.markdown("""
    ### HIDU Surgical Planning Studio
    
    **Professional Features:**
    - ✨ Smooth continuous surface drawing
    - 📍 Draggable colored annotations
    - 📏 Distance & angle measurements
    - 📐 **Skin Flap Area Calculation** (mm²)
    - 🏷️ Draggable floating labels with delete
    - 📄 PDF export with 3 views + data
    - 💾 Save/Load projects (.json)
    - 🎨 Medical color coding
    - 📱 iPad & touch optimized
    - 🎛️ Collapsible UI
    
    **Clinical Workflow:**
    1. Upload 3D scan → Calibrate
    2. Draw surgical markings (Brush)
    3. **Draw closed loop for flap area**
    4. Measure distances & angles
    5. Add annotations with notes
    6. Drag labels to optimal positions
    7. Save project for later
    8. Export PDF for medical records
    
    **Optimized for:**
    - **Skin Flap Surgery** (area calculation)
    - Rhinoplasty planning
    - Facial reconstructive surgery
    - Tumor excision planning
    - Maxillofacial procedures
    - Pre-operative documentation
    
    **New: Area Measurement**
    - Draw around tumor/defect with Brush
    - Auto-detects closed loops
    - Calculates true 3D surface area
    - Shows result in mm² (calibrated)
    - Ideal for flap planning!
    """)
