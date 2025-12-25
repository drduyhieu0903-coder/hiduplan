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

            /* ANNOTATION LABEL */
            .annotation-label {{
                position: absolute;
                background: rgba(33, 150, 243, 0.95);
                color: white;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                pointer-events: all;
                cursor: move;
                z-index: 1000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                border: 2px solid rgba(255,255,255,0.3);
                min-width: 120px;
                touch-action: none;
                user-select: none;
                transition: box-shadow 0.2s;
            }}
            
            .annotation-label:hover {{
                box-shadow: 0 6px 20px rgba(33,150,243,0.6);
                border-color: rgba(255,255,255,0.5);
            }}
            
            .annotation-label.dragging {{
                opacity: 0.8;
                box-shadow: 0 8px 24px rgba(33,150,243,0.8);
                transform: scale(1.05);
                cursor: grabbing;
            }}
            
            .annotation-header {{
                display: flex;
                align-items: center;
                margin-bottom: 4px;
                cursor: grab;
                padding: 2px 0;
            }}
            
            .annotation-header:active {{
                cursor: grabbing;
            }}
            
            .annotation-number {{
                display: inline-block;
                width: 24px;
                height: 24px;
                background: white;
                color: #2196f3;
                border-radius: 50%;
                text-align: center;
                line-height: 24px;
                font-weight: bold;
                margin-right: 8px;
            }}
            
            .annotation-input {{
                background: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.3);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                margin-top: 6px;
                width: 100%;
                font-size: 11px;
            }}
            
            .annotation-input::placeholder {{
                color: rgba(255,255,255,0.6);
            }}

            /* VIEW NAVIGATION */
            .nav-panel {{
                position: absolute; top: 20px; right: 20px;
                background: linear-gradient(135deg, rgba(13, 71, 161, 0.95), rgba(25, 118, 210, 0.95));
                backdrop-filter: blur(15px);
                border-radius: 16px;
                padding: 15px;
                border: 2px solid rgba(255,255,255,0.15);
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                touch-action: none;
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

        </style>
        
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/OBJLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/MTLLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/tween.js/18.6.4/tween.umd.js"></script>
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
                <button class="close-panel-btn" onclick="toggleSettingsPanel()" title="Hide Settings (Click tool again to show)">×</button>
            </div>
            
            <!-- Medical Color Presets -->
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
                <input type="range" id="p-width" class="slider" min="0.002" max="0.012" step="0.001" value="0.003" oninput="updateSettings()">
                <span class="value-display" id="width-val">3</span>
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
            
            <!-- Measurement Display -->
            <div id="measure-box" style="display:none;">
                <div class="measurement-box">
                    <div class="measurement-label" id="measure-label">MEASUREMENT</div>
                    <div class="measurement-value" id="measure-value">0.0 mm</div>
                </div>
            </div>
        </div>

        <div id="info-hud" class="info-hud">Select a tool to start</div>

        <!-- VIEW NAVIGATION -->
        <div class="nav-panel">
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
            let eraserRadius = 0.05; // Relative to currentZoom
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
            
            // iPad touch handling
            let touchStartTime = 0;
            let longPressTimer = null;
            
            // Settings
            let settings = {{
                color: 0x9C27B0,
                colorHex: '#9C27B0',
                lineWidth: 0.003,
                opacity: 0.95,
                offsetFactor: 0.0001
            }};
            
            let settingsPanelVisible = false;

            function init() {{
                scene = new THREE.Scene();
                scene.background = new THREE.Color(0x1a1a1a);

                camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 2000);
                renderer = new THREE.WebGLRenderer({{ antialias: true }});
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
                
                // Prevent context menu and default touch behaviors
                canvas.addEventListener('contextmenu', (e) => e.preventDefault());
                document.addEventListener('contextmenu', (e) => e.preventDefault());
                
                // Touch events for iPad
                canvas.addEventListener('touchstart', onTouchStart, {{ passive: false }});
                canvas.addEventListener('touchmove', onTouchMove, {{ passive: false }});
                canvas.addEventListener('touchend', onTouchEnd, {{ passive: false }});
                
                // Mouse events for desktop
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
                
                // Clear any existing long press timer
                if(longPressTimer) {{
                    clearTimeout(longPressTimer);
                    longPressTimer = null;
                }}
                
                // Single touch - treat as pointer down
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
                
                // Clear long press if moving
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
                
                // Only trigger onUp if it was a quick tap (not a long press)
                if(touchDuration < 500 && currentTool !== 'view') {{
                    const fakeEvent = {{ button: 0 }};
                    onUp(fakeEvent);
                }}
            }}

            // --- TOOL SYSTEM ---
            window.selectTool = function(tool) {{
                // Toggle settings panel if clicking same tool
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
                        hud.innerText = "Click and drag to draw continuously on surface"; 
                    }}
                    else if(tool === 'eraser') {{
                        tName.innerText = "ERASER TOOL";
                        hud.innerText = "Click and drag to erase lines and annotations";
                        createEraserCursor();
                    }}
                    else if(tool === 'line') {{ 
                        tName.innerText = "SURGICAL MARKING LINE"; 
                        hud.innerText = "Click two points to draw line"; 
                    }}
                    else if(tool === 'annotation') {{
                        tName.innerText = "ANNOTATION TOOL";
                        hud.innerText = "Click to place numbered annotation marker";
                    }}
                    else if(tool === 'distance') {{ 
                        tName.innerText = "DISTANCE MEASUREMENT"; 
                        hud.innerText = "Click two points to measure distance";
                        measureBox.style.display = 'block';
                        document.getElementById('measure-label').innerText = "DISTANCE";
                    }}
                    else if(tool === 'angle') {{ 
                        tName.innerText = "ANGLE MEASUREMENT"; 
                        hud.innerText = "Click 3 points: Vertex → Point 1 → Point 2";
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
                
                document.getElementById('width-val').innerText = (settings.lineWidth * 1000).toFixed(0);
                document.getElementById('opacity-val').innerText = settings.opacity.toFixed(2);
                document.getElementById('offset-val').innerText = settings.offsetFactor.toFixed(5);
                
                // Update eraser size
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
                            addMarker(point, 0xff0000);
                        }} else {{
                            measurePoints.push(point);
                            addMarker(point, 0xff0000);
                            
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
                // Update eraser cursor position
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
                if(now - lastDrawTime < 16) return; // Throttle to ~60fps
                lastDrawTime = now;

                const hits = getIntersects(event);
                if (hits.length > 0) {{
                    const point = getOffsetPoint(hits[0]);

                    if (currentTool === 'brush') {{
                        const lastPoint = drawPoints[drawPoints.length - 1];
                        
                        // Smooth continuous drawing with smaller threshold
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
                    
                    // Finalize the stroke
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
                // Remove old temp meshes
                tempMeshes.forEach(m => scene.remove(m));
                tempMeshes = [];
                
                if(drawPoints.length < 2) return;
                
                // Create tube geometry for thickness
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
            }}

            function addMarker(point, color) {{
                const geo = new THREE.SphereGeometry(currentZoom * 0.002, 16, 16);
                const mat = new THREE.MeshBasicMaterial({{ color: color, depthTest: false }});
                const marker = new THREE.Mesh(geo, mat);
                marker.position.copy(point);
                marker.renderOrder = 1000;
                scene.add(marker);
                measureMarkers.push(marker);
            }}

            // --- ANNOTATION TOOL ---
            function createAnnotation(point3D, event) {{
                // Create 3D marker
                const markerGeo = new THREE.SphereGeometry(currentZoom * 0.003, 16, 16);
                const markerMat = new THREE.MeshBasicMaterial({{ color: 0x2196f3, depthTest: false }});
                const marker = new THREE.Mesh(markerGeo, markerMat);
                marker.position.copy(point3D);
                marker.renderOrder = 1001;
                scene.add(marker);
                
                // Create HTML label
                const label = document.createElement('div');
                label.className = 'annotation-label';
                label.innerHTML = `
                    <span class="annotation-number">${{annotationCounter}}</span>
                    <input type="text" 
                           class="annotation-input" 
                           placeholder="Enter note..."
                           onkeydown="event.stopPropagation()"
                           ontouchstart="event.stopPropagation()"
                           ontouchmove="event.stopPropagation()">
                `;
                
                document.body.appendChild(label);
                
                // Position label
                const screenPos = toScreenPosition(point3D);
                label.style.left = screenPos.x + 'px';
                label.style.top = screenPos.y + 'px';
                
                // Store annotation data
                const annotation = {{
                    id: annotationCounter,
                    point3D: point3D,
                    marker: marker,
                    label: label
                }};
                annotations.push(annotation);
                drawnObjects.push(marker);
                
                annotationCounter++;
                
                // Update label position on render
                function updateLabelPosition() {{
                    if(!label.parentElement) return;
                    const pos = toScreenPosition(point3D);
                    label.style.left = pos.x + 'px';
                    label.style.top = pos.y + 'px';
                    requestAnimationFrame(updateLabelPosition);
                }}
                updateLabelPosition();
            }}

            // ==========================================
            // ERASER TOOL - CHÈN HÀM TẨY Ở ĐÂY
            // ==========================================
            
            function createEraserCursor() {{
                // Remove old cursor if exists
                if(eraserCursor) {{
                    scene.remove(eraserCursor);
                }}
                
                // Create semi-transparent sphere as eraser cursor
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
                
                // Show/hide eraser size slider
                document.getElementById('eraser-size-row').style.display = 'flex';
            }}
            
            function eraseAtPoint(point) {{
                const eraseRadiusWorld = eraserRadius * currentZoom;
                let erasedSomething = false;
                
                // Check all drawn objects
                for(let i = drawnObjects.length - 1; i >= 0; i--) {{
                    const obj = drawnObjects[i];
                    
                    // Check if object is within eraser radius
                    if(obj.geometry && obj.geometry.attributes && obj.geometry.attributes.position) {{
                        const positions = obj.geometry.attributes.position.array;
                        let shouldErase = false;
                        
                        // Check vertices
                        for(let j = 0; j < positions.length; j += 3) {{
                            const vertex = new THREE.Vector3(
                                positions[j],
                                positions[j + 1],
                                positions[j + 2]
                            );
                            
                            // Transform to world space
                            vertex.applyMatrix4(obj.matrixWorld);
                            
                            // Check distance to eraser point
                            if(vertex.distanceTo(point) < eraseRadiusWorld) {{
                                shouldErase = true;
                                break;
                            }}
                        }}
                        
                        if(shouldErase) {{
                            scene.remove(obj);
                            if(obj.geometry) obj.geometry.dispose();
                            if(obj.material) obj.material.dispose();
                            
                            // Remove annotation label if exists
                            const annotation = annotations.find(a => a.marker === obj);
                            if(annotation) {{
                                annotation.label.remove();
                                annotations = annotations.filter(a => a !== annotation);
                            }}
                            
                            drawnObjects.splice(i, 1);
                            erasedSomething = true;
                        }}
                    }}
                    // Handle sphere markers (annotations, measurements)
                    else if(obj.type === 'Mesh' && obj.geometry && obj.geometry.type === 'SphereGeometry') {{
                        if(obj.position.distanceTo(point) < eraseRadiusWorld) {{
                            scene.remove(obj);
                            if(obj.geometry) obj.geometry.dispose();
                            if(obj.material) obj.material.dispose();
                            
                            // Remove annotation label if exists
                            const annotation = annotations.find(a => a.marker === obj);
                            if(annotation) {{
                                annotation.label.remove();
                                annotations = annotations.filter(a => a !== annotation);
                            }}
                            
                            drawnObjects.splice(i, 1);
                            erasedSomething = true;
                        }}
                    }}
                }}
                
                return erasedSomething;
            }}
            
            // ==========================================
            // KẾT THÚC ERASER TOOL
            // ==========================================

            function toScreenPosition(point3D) {{
                const vector = point3D.clone();
                vector.project(camera);
                
                const rect = renderer.domElement.getBoundingClientRect();
                return {{
                    x: (vector.x + 1) / 2 * rect.width + rect.left,
                    y: -(vector.y - 1) / 2 * rect.height + rect.top
                }};
            }}

            function measureDistance(p1, p2) {{
                const dist = p1.distanceTo(p2) * SCALE_FACTOR;
                document.getElementById('measure-value').innerText = dist.toFixed(2) + ' mm';
                
                drawSurfaceLine(p1, p2);
                
                setTimeout(() => {{
                    measureMarkers.forEach(m => scene.remove(m));
                    measureMarkers = [];
                }}, 3000);
            }}

            function handleAngleMeasurement(point) {{
                measurePoints.push(point);
                addMarker(point, 0xffff00);
                
                if(measurePoints.length === 1) {{
                    document.getElementById('info-hud').innerText = "Vertex set. Click Point 1";
                }}
                else if(measurePoints.length === 2) {{
                    document.getElementById('info-hud').innerText = "Point 1 set. Click Point 2";
                    drawSurfaceLine(measurePoints[0], measurePoints[1]);
                }}
                else if(measurePoints.length === 3) {{
                    const v1 = measurePoints[1].clone().sub(measurePoints[0]).normalize();
                    const v2 = measurePoints[2].clone().sub(measurePoints[0]).normalize();
                    const angle = THREE.MathUtils.radToDeg(v1.angleTo(v2));
                    
                    document.getElementById('measure-value').innerText = angle.toFixed(1) + '°';
                    document.getElementById('info-hud').innerText = "Angle measured";
                    
                    drawSurfaceLine(measurePoints[0], measurePoints[2]);
                    
                    setTimeout(() => {{
                        measureMarkers.forEach(m => scene.remove(m));
                        measureMarkers = [];
                        measurePoints = [];
                    }}, 4000);
                }}
            }}

            // --- UTILITIES ---
            window.undo = function() {{
                if (drawnObjects.length > 0) {{
                    const obj = drawnObjects.pop();
                    scene.remove(obj);
                    if(obj.geometry) obj.geometry.dispose();
                    if(obj.material) obj.material.dispose();
                    
                    // Remove annotation label if it exists
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
                
                // Hide eraser cursor and settings
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
    
    st.markdown("### 🎯 Quick Guide")
    st.markdown("""
    **Drawing Tools:**
    - 🖱️ **View**: Rotate and zoom model
    - 🖌️ **Brush**: Freehand continuous marking
    - 🧹 **Eraser**: Remove lines and annotations
    - 📏 **Line**: Straight surgical lines
    - 📍 **Annotation**: Place numbered notes
    
    **Measurement Tools:**
    - 📐 **Distance**: Measure between points (mm)
    - 📊 **Angle**: Measure angles (degrees)
    
    **Navigation:**
    - **View buttons**: Jump to anatomical views
    - **Arrow controls**: Manual rotation
    - **Front**: Direct facial view
    - **Left/Right**: Profile views
    
    **Annotation Tips:**
    - 📍 **Click** to place numbered marker
    - 🖱️ **Drag header** to reposition label
    - 📝 **Type notes** in text field
    - ✨ Label follows 3D point when rotating
    - 📌 Custom position stays after moving
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
    ### Welcome to HIDU Surgical Planning Studio
    
    **Professional Features:**
    - ✨ Continuous smooth surface drawing
    - 📍 Numbered annotation markers with notes
    - 📏 Accurate distance & angle measurements
    - 🎨 Medical-standard color coding
    - 📱 iPad & touch optimized
    
    **Optimized for:**
    - Rhinoplasty planning
    - Facial reconstructive surgery
    - Orthognathic surgery
    - Dental implant planning
    
    **Perfect for iPad:**
    - No scroll conflicts during drawing
    - No long-press context menus
    - Smooth continuous line rendering
    - Touch-optimized controls
    """)
