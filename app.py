from flask import Flask, render_template, request, jsonify, url_for
from datetime import datetime, timedelta
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MUSIC_FOLDER'] = 'static/music'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MUSIC_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}

# Create folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MUSIC_FOLDER'], exist_ok=True)

def allowed_file(filename, extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions

def calculate_monthsary(start_date):
    today = datetime.now().date()
    months = (today.year - start_date.year) * 12 + (today.month - start_date.month)
    days = today.day - start_date.day
    
    if days < 0:
        months -= 1
        last_day = (today.replace(day=1) - timedelta(days=1)).day
        days = last_day + days
    
    if months >= 0:
        next_month = today.month + 1
        next_year = today.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        try:
            next_monthsary = datetime(next_year, next_month, start_date.day).date()
        except ValueError:
            next_monthsary = datetime(next_year, next_month, 28).date()
        days_until = (next_monthsary - today).days
    else:
        days_until = None
    
    return {
        'months': max(0, months),
        'days': days if months >= 0 else None,
        'days_until': days_until,
        'start_date': start_date.strftime('%B %d, %Y'),
        'total_days': (today - start_date).days
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ""
    monthsary_data = None
    photos = []
    love_message = ""
    music_url = None
    
    saved_data = load_saved_data()
    if saved_data:
        photos = saved_data.get('photos', [])
        love_message = saved_data.get('love_message', '')
        music_url = saved_data.get('music_url')
    
    if request.method == 'POST':
        if 'start_date' in request.form:
            start_date_str = request.form.get('start_date')
            if start_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                    monthsary_data = calculate_monthsary(start_date)
                    message = f"🎉 Happy {monthsary_data['months']}th Monthsary! 🎉"
                    save_data({'start_date': start_date_str})
                except Exception as e:
                    message = f"Error: {str(e)}"
        
        if 'love_message' in request.form:
            love_message = request.form.get('love_message', '').strip()
            if love_message:
                save_data({'love_message': love_message})
                message = "💕 Your love message has been saved!"
                saved_data = load_saved_data()
                love_message = saved_data.get('love_message', '')
        
        if 'photos' in request.files:
            files = request.files.getlist('photos')
            uploaded_count = 0
            
            for file in files:
                if file and file.filename != '' and allowed_file(file.filename, ALLOWED_EXTENSIONS):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                    filename = secure_filename(f"photo_{timestamp}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    photo_url = url_for('static', filename=f'uploads/{filename}')
                    
                    current_data = load_saved_data()
                    photos_list = current_data.get('photos', [])
                    photos_list.append(photo_url)
                    save_data({'photos': photos_list})
                    uploaded_count += 1
            
            saved_data = load_saved_data()
            photos = saved_data.get('photos', [])
            
            if uploaded_count > 0:
                message = f"✅ {uploaded_count} photo(s) uploaded successfully!"
            else:
                message = "❌ No valid photos uploaded."
        
        if 'music' in request.files:
            file = request.files['music']
            if file and file.filename != '':
                if allowed_file(file.filename, ALLOWED_MUSIC_EXTENSIONS):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = secure_filename(f"music_{timestamp}_{file.filename}")
                    filepath = os.path.join(app.config['MUSIC_FOLDER'], filename)
                    file.save(filepath)
                    
                    music_url = url_for('static', filename=f'music/{filename}')
                    save_data({'music_url': music_url})
                    message = "✅ Music uploaded successfully!"
                else:
                    message = "❌ Please upload MP3, WAV, OGG, or M4A"
            else:
                message = "❌ No file selected"
    
    saved_date = load_saved_data().get('start_date')
    if saved_date and not monthsary_data:
        try:
            start_date = datetime.strptime(saved_date, '%Y-%m-%d').date()
            monthsary_data = calculate_monthsary(start_date)
            message = f"🎉 Happy {monthsary_data['months']}th Monthsary! 🎉"
        except:
            pass
    
    return render_template('index.html', 
                         message=message, 
                         monthsary_data=monthsary_data,
                         today=datetime.now().strftime('%Y-%m-%d'),
                         photos=photos,
                         love_message=love_message,
                         music_url=music_url)

@app.route('/clear_photos', methods=['POST'])
def clear_photos():
    saved_data = load_saved_data()
    photos = saved_data.get('photos', [])
    
    for photo_url in photos:
        filename = photo_url.split('/')[-1]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass
    
    save_data({'photos': []})
    return jsonify({'success': True})

@app.route('/reset', methods=['POST'])
def reset_data():
    try:
        for file in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except:
                pass
        
        for file in os.listdir(app.config['MUSIC_FOLDER']):
            file_path = os.path.join(app.config['MUSIC_FOLDER'], file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except:
                pass
        
        if os.path.exists('user_data.json'):
            os.remove('user_data.json')
        
        return jsonify({'success': True})
    except:
        return jsonify({'success': False})

def save_data(data):
    try:
        with open('user_data.json', 'r') as f:
            saved = json.load(f)
    except:
        saved = {}
    saved.update(data)
    with open('user_data.json', 'w') as f:
        json.dump(saved, f)

def load_saved_data():
    try:
        with open('user_data.json', 'r') as f:
            return json.load(f)
    except:
        return {}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)