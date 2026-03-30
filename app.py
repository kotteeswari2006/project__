from flask import Flask, render_template, request, send_file
import os
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS
from datetime import datetime, timedelta
from fpdf import FPDF

app = Flask(__name__)
UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

last_result = {}
verification_history = []

def get_metadata(path):
    meta_info = {}
    try:
        img = Image.open(path)
        info = img._getexif()
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                meta_info[decoded] = value
    except: pass
    return meta_info

def perform_ela(original_path, quality_level):
    temp_ela = 'temp_ela.jpg'
    original = Image.open(original_path).convert('RGB')
    original.save(temp_ela, 'JPEG', quality=int(quality_level))
    temporary = Image.open(temp_ela)
    ela_image = ImageChops.difference(original, temporary)
    pixels = np.array(ela_image)
    mean_noise = np.mean(pixels)
    accuracy = max(40, 100 - (mean_noise * (int(quality_level)/25))) 
    extrema = ela_image.getextrema()
    max_diff = max([ex[1] for ex in extrema]) or 1
    scale = 255.0 / max_diff
    ela_image = ImageEnhance.Brightness(ela_image).enhance(scale)
    ela_path = os.path.join(app.config['UPLOAD_FOLDER'], 'ela_result.jpg')
    ela_image.save(ela_path)
    os.remove(temp_ela)
    return 'ela_result.jpg', round(accuracy, 2)

@app.route('/')
def main_dashboard():
    return render_template('main_dashboard.html')

@app.route('/scan_page')
def scan_page():
    return render_template('index.html')

@app.route('/metadata')
def show_metadata():
    return render_template('metadata.html', result=last_result)

@app.route('/history')
def show_history():
    return render_template('history.html', history=verification_history)

@app.route('/download_report')
def download_report():
    if not last_result: return "No Scan Data Available"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "FORENSIC VERIFICATION REPORT", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(100, 10, f"File: {last_result['filename']}")
    pdf.cell(90, 10, f"Date: {last_result['datetime']}", ln=True)
    pdf.cell(100, 10, f"Score: {last_result['score']}%")
    pdf.cell(90, 10, f"Status: {last_result['status']}", ln=True)
    pdf.output("report.pdf")
    return send_file("report.pdf", as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    global last_result, verification_history
    file = request.files['file']
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        ist_now = datetime.now() + timedelta(hours=5, minutes=30)
        scan_time = ist_now.strftime("%d-%m-%Y | %I:%M:%S %p")
        meta = get_metadata(filepath)
        ela_res, score = perform_ela(filepath, 90)
        software = meta.get('Software', 'None')
        device = meta.get('Model', 'Unknown')
        status = "TAMPERED" if (score < 85 or "Photoshop" in str(software)) else "AUTHENTIC"
        color = "#ef4444" if status == "TAMPERED" else "#10b981"
        last_result = {'status': status, 'score': score, 'filename': file.filename, 'software': software, 'device': device, 'datetime': scan_time, 'color': color}
        verification_history.insert(0, last_result)
        
        return f"""
        <html>
            <head>
                <title>Forensic Result</title>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; background: #0b1120; color: white; text-align: center; padding: 20px; margin: 0; }}
                    .container {{ max-width: 1100px; margin: 20px auto; background: #111827; padding: 40px; border-radius: 30px; border: 1px solid #1f2937; }}
                    
                    /* Circular Gauge Style */
                    .circular-progress {{
                        position: relative; width: 180px; height: 180px; margin: 20px auto;
                        background: conic-gradient({color} {score * 3.6}deg, #1e293b 0deg);
                        border-radius: 50%; display: flex; align-items: center; justify-content: center;
                        box-shadow: 0 0 20px {color}44;
                    }}
                    .circular-progress::before {{
                        content: ''; position: absolute; width: 150px; height: 150px;
                        background: #111827; border-radius: 50%;
                    }}
                    .percentage-text {{ position: relative; font-size: 32px; font-weight: 900; color: {color}; }}
                    
                    .verdict-badge {{ margin-top: 15px; padding: 10px 40px; border-radius: 8px; background: rgba(0,0,0,0.3); border-left: 5px solid {color}; font-size: 20px; font-weight: bold; color: {color}; display: inline-block; }}
                    .image-comparison {{ display: flex; justify-content: center; gap: 20px; margin: 40px 0; }}
                    .img-box {{ flex: 1; background: #0f172a; padding: 15px; border-radius: 15px; border: 1px solid #334155; }}
                    img {{ width: 100%; border-radius: 10px; }}
                    .btn {{ padding: 12px 20px; border-radius: 8px; text-decoration: none; color: white; font-weight: bold; margin: 5px; display: inline-flex; }}
                    .btn-blue {{ background: #2563eb; }} .btn-gray {{ background: #374151; }} .btn-red {{ background: #dc2626; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 style="color: #3b82f6;">FORENSIC SCAN COMPLETE</h1>
                    <div style="background: #1e293b; padding: 25px; border-radius: 20px; display: inline-block;">
                        <div style="color: #94a3b8; font-size: 12px; letter-spacing: 2px;">INTEGRITY SCORE</div>
                        <div class="circular-progress"><span class="percentage-text">{score}%</span></div>
                        <div class="verdict-badge">{status}</div>
                    </div>
                    <div class="image-comparison">
                        <div class="img-box"><img src="/static/{file.filename}"><p style="color:#64748b;">ORIGINAL</p></div>
                        <div class="img-box"><img src="/static/ela_result.jpg"><p style="color:#64748b;">ELA SCAN</p></div>
                    </div>
                    <div style="margin-top: 30px;">
                        <a href="/" class="btn btn-gray">🏠 DASHBOARD</a>
                        <a href="/scan_page" class="btn btn-blue">➕ NEW SCAN</a>
                        <a href="/metadata" class="btn btn-blue" style="background:#4f46e5;">📊 METADATA</a>
                        <a href="/history" class="btn btn-gray">📜 HISTORY</a>
                        <a href="/download_report" class="btn btn-red">📄 DOWNLOAD PDF</a>
                    </div>
                </div>
            </body>
        </html>
        """

if __name__ == '__main__':
    app.run(debug=True)