import os
from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import time

# PERBAIKAN: Menggunakan __name__
app = Flask(__name__)
app.secret_key = '$%#@' # Ganti ini dengan kunci yang lebih aman

# --- KONFIGURASI DATABASE ---
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'web-porto'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' 

mysql = MySQL(app)

# --- KONFIGURASI UPLOAD ---
UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# --- RUTE PUBLIK ---
@app.route('/')
def home():
    cur = mysql.connection.cursor()
    
    # BARU: Mengambil data profil untuk ditampilkan di home
    # (Asumsi admin/pemilik portofolio adalah user dengan id = 1)
    cur.execute("SELECT * FROM users WHERE id = 1")
    profile = cur.fetchone()
    
    cur.execute("SELECT * FROM skills")
    skills = cur.fetchall()
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()
    cur.close()
    
    # BARU: Menambahkan 'profile' ke template
    return render_template('home.html', profile=profile, skills=skills, projects=projects)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (user, pwd))
        account = cur.fetchone()
        cur.close()

        if account:
            session['user_id'] = account['id']
            session['username'] = account['username']
            flash('Login berhasil.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau password salah.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('home'))

# --- RUTE ADMIN (DASHBOARD) ---
# Rute ini sudah menangani semua logika CRUD
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    
    # Ambil data profil admin yang sedang login
    cur.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    profile = cur.fetchone()

    action = request.args.get('action')
    id = request.args.get('id')
    
    # --- LOGIKA POST (CREATE & UPDATE) ---
    if request.method == 'POST':
        
        # Aksi: Update Profil (U dari CRUD)
        if action == 'main':
            name = request.form['name']
            bio = request.form['bio']
            
            photo_path = profile['photo'] # Ambil nama foto yang lama
            if 'photo' in request.files:
                file = request.files['photo']
                if file and allowed_file(file.filename):
                    filename = str(int(time.time())) + '_' + secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    photo_path = filename # Ganti dengan nama foto yang baru
            
            cur.execute("UPDATE users SET name=%s, bio=%s, photo=%s WHERE id=%s", 
                        (name, bio, photo_path, session['user_id']))
            
            mysql.connection.commit()
            flash('Profil berhasil diperbarui.', 'success')
            return redirect(url_for('dashboard'))

        # Aksi: Tambah Skill (C dari CRUD)
        if action == 'add_skill':
            name = request.form['name']
            level = request.form['level']
            icon = request.form['icon']
            cur.execute("INSERT INTO skills (name, level, icon) VALUES (%s, %s, %s)", (name, level, icon))
            mysql.connection.commit()
            flash('Skill berhasil ditambahkan.', 'success')
            return redirect(url_for('dashboard'))

        # Aksi: Edit Skill (U dari CRUD)
        if action == 'edit_skill' and id:
            name = request.form['name']
            level = request.form['level']
            icon = request.form['icon']
            cur.execute("UPDATE skills SET name=%s, level=%s, icon=%s WHERE id=%s", (name, level, icon, id))
            mysql.connection.commit()
            flash('Skill berhasil diperbarui.', 'success')
            return redirect(url_for('dashboard'))

        # Aksi: Tambah Proyek (C dari CRUD)
        if action == 'add_project':
            title = request.form['title']
            desc = request.form['description']
            link = request.form['link']
            image_path = ''
            
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = str(int(time.time())) + '_' + secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_path = filename 

            cur.execute("INSERT INTO projects (title, description, link, image) VALUES (%s, %s, %s, %s)", 
                        (title, desc, link, image_path))
            mysql.connection.commit()
            flash('Proyek berhasil ditambahkan.', 'success')
            return redirect(url_for('dashboard'))

        # Aksi: Edit Proyek (U dari CRUD)
        if action == 'edit_project' and id:
            title = request.form['title']
            desc = request.form['description']
            link = request.form['link']
            
            # Ambil data proyek saat ini untuk foto lama
            cur.execute("SELECT image FROM projects WHERE id = %s", (id,))
            project_img = cur.fetchone()['image']

            if 'image' in request.files and request.files['image'].filename != '':
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = str(int(time.time())) + '_' + secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    project_img = filename # Ganti dengan foto baru
                    cur.execute("UPDATE projects SET title=%s, description=%s, link=%s, image=%s WHERE id=%s",
                                (title, desc, link, project_img, id))
                else:
                    flash('Format file gambar tidak diizinkan.', 'danger')
                    return redirect(request.url)
            else:
                # Update tanpa mengubah gambar
                cur.execute("UPDATE projects SET title=%s, description=%s, link=%s WHERE id=%s",
                            (title, desc, link, id))

            mysql.connection.commit()
            flash('Proyek berhasil diperbarui.', 'success')
            return redirect(url_for('dashboard'))

    # --- LOGIKA GET (READ DARI CRUD) ---
    
    # Tampilkan form Tambah Skill
    if action == 'add_skill':
        return render_template('dashboard.html', action=action, title='Tambah Skill', admin_name=session['username'])

    # Tampilkan form Edit Skill
    if action == 'edit_skill' and id:
        cur.execute("SELECT * FROM skills WHERE id = %s", (id,))
        skill = cur.fetchone()
        return render_template('dashboard.html', action=action, title='Edit Skill', skill=skill, admin_name=session['username'])

    # Tampilkan form Tambah Proyek
    if action == 'add_project':
        return render_template('dashboard.html', action=action, title='Tambah Proyek', admin_name=session['username'])

    # Tampilkan form Edit Proyek
    if action == 'edit_project' and id:
        cur.execute("SELECT * FROM projects WHERE id = %s", (id,))
        project = cur.fetchone()
        return render_template('dashboard.html', action=action, title='Edit Proyek', project=project, admin_name=session['username'])

    # Tampilan default dashboard (Read dari CRUD)
    cur.execute("SELECT * FROM skills ORDER BY id DESC")
    skills = cur.fetchall()
    cur.execute("SELECT * FROM projects ORDER BY id DESC")
    projects = cur.fetchall()
    cur.close()
    
    return render_template('dashboard.html', 
                           profile=profile, 
                           skills=skills, 
                           projects=projects, 
                           admin_name=session['username'])

# --- RUTE DELETE (D DARI CRUD) ---
@app.route('/delete_skill/<int:id>', methods=['POST'])
def delete_skill(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM skills WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Skill berhasil dihapus.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/delete_project/<int:id>', methods=['POST'])
def delete_project(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM projects WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Proyek berhasil dihapus.', 'info')
    return redirect(url_for('dashboard'))


# PERBAIKAN: Menggunakan __name__
if __name__ == '__main__':
    app.run(debug=True)