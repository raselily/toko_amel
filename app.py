from flask import Flask,redirect,url_for,render_template,request,jsonify,session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson import ObjectId
import re
import json
import os
from os.path import join, dirname
from werkzeug.utils import secure_filename 
from datetime import datetime
from collections import defaultdict
from flask import send_from_directory
import random
import string

import os
from os.path import join, dirname
from dotenv import load_dotenv

load_dotenv()

import midtransclient
snap = midtransclient.Snap(
    # Set to true if you want Production Environment (accept real transaction).
    is_production=False,
    server_key='SB-Mid-server-XlJJabiASRiCCX7WSvSCsPpx'
)

password = os.getenv('MONGO_PASSWORD')
cxn_str = os.getenv('MONGODB_URI')
client = MongoClient(cxn_str)
dbname = os.getenv('DB_NAME')
db = client[dbname]

app=Flask(__name__)
app.jinja_env.globals.update(enumerate=enumerate)
app.secret_key = 'Ndutkucingku2'

UPLOAD_FOLDER = os.path.join('static', 'assets', 'img')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_cart():
    if 'email' in session:
        email = session['email']
        cart_data = session.get(email, '[]')
        try:
            cart = json.loads(cart_data)
        except json.JSONDecodeError:
            cart = []
    else:
        cart = []
    return cart

def save_cart(cart):
    if 'email' in session:
        email = session['email']
        # Simpan keranjang ke session berdasarkan email
        session['cart'] = cart

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def upload_file(filename):
    upload_folder = app.config.get('UPLOAD_FOLDER', 'static/assets/img')
    return send_from_directory(upload_folder, filename)

def is_logged_in():
    return 'logged_in' in session and session['logged_in']

@app.context_processor
def utility_processor():
    def is_logged_in():
        return 'logged_in' in session and session['logged_in']
    return dict(is_logged_in=is_logged_in)

@app.route('/',methods=['GET','POST'])
def home():
    produk = get_produk()
    print(produk)
    return render_template('index.html', produk=produk)

@app.route('/daftar',methods=['GET','POST'])
def daftar():
    if request.method == 'POST':
        nama = request.form['nama']
        noHp = request.form['noHp'] 
        email = request.form['email']
        password = request.form['password']
        
        email_regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.match(email_regex, email):
            return jsonify({'result': 'failure', 'msg': 'Password belum sesuai'})
        hashed_password = generate_password_hash(password)
        if db.users.find_one({'email': email}):
            return jsonify({'result': 'failure', 'msg': 'Email sudah terdaftar'})
        
        registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.users.insert_one({
            'nama': nama,
            'noHp': noHp,
            'email': email,
            'password': hashed_password,
            'registration_date': registration_date,
        })
        return jsonify({'result': 'success'})
    return render_template('daftar.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.form.get('email_user')
            password = request.form.get('password_user')
            
            if not email or not password:
                return jsonify({'result': 'failure', 'msg': 'Email atau password tidak boleh kosong'}), 400
            
            user = db.users.find_one({'email': email})
            
            if user and check_password_hash(user['password'], password):
                session['logged_in'] = True
                session['email'] = email
                return jsonify({'result': 'success', 'msg': 'Login successful'})
            
            return jsonify({'result': 'failure', 'msg': 'Email atau password salah'})
        
        return render_template('login.html')
    except Exception as e:
        # Cetak error ke terminal untuk debugging
        print(f"Error saat login: {e}")
        return jsonify({'result': 'failure', 'msg': 'Terjadi kesalahan pada server'}), 500

@app.route('/check_login_status', methods=['GET'])
def check_login_status():
    logged_in = session.get('logged_in', False)
    if logged_in:
        email = session.get('email', 'User')
        print(email)
        return jsonify({'logged_in': True, 'email': email})
    return jsonify({'logged_in': False})

@app.route('/profil',methods=['GET','POST'])
def profile():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    email = session['email']
    user = db.users.find_one({'email': email})
    if not user:
        return jsonify({'result': 'failure', 'msg': 'Email tidak ditemukan'})
    return render_template('profil.html', user=user)

@app.route('/get_user_data', methods=['GET'])
def get_user_data():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'result': 'failure', 'msg': 'User belum login'}), 401
    email = session['email']
    user = db.users.find_one({'email': email}, {'_id': 0, 'nama': 1, 'email': 1, 'noHp': 1,})
    if user:
        return jsonify(user), 200
    return jsonify({'result': 'failure', 'msg': 'User tidak ditemukan'}), 404

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'logged_in' not in session or not session['logged_in']:
        return jsonify({'result': 'failure', 'msg': 'User belum login'}), 401
    data = request.json
    email = session['email']
    update_data = {
        'nama': data.get('nama'),
        'noHp': data.get('noHp'),
    }
    db.users.update_one({'email': email}, {'$set': update_data})
    return jsonify({'result': 'success'}), 200

@app.route('/produk', methods=['GET'])
def produk():
    produk_list = list(db.produk.find())
    for produk in produk_list:
        produk['_id'] = str(produk['_id'])  # Konversi ObjectId ke string
    return render_template('produk.html', produk=produk_list)

@app.route('/about',methods=['GET','POST'])
def about():
    return render_template('about.html')

@app.route('/',methods=['GET'])
def get_produk():
    # Ambil hanya 5 produk dari koleksi
    produk = db.produk.find({}, {"_id": 1, "name": 1, "price": 1, "image": 1, "quantity":1}).limit(5)
    return list(produk)

@app.route('/hapus_dari_keranjang/<productId>', methods=['POST'])
def hapus_dari_keranjang(productId):
    if productId:
        cart = session.get('cart', [])
        print(cart)
        # Find the index of the item to be removed
        cart = [item for item in cart if str(item.get('product_id')) != str(productId)]
        
        # Update the session with the modified cart
        session['cart'] = cart
        return jsonify({
        'status': True,
    })
        
    else:
        return jsonify({'success': False, 'message': 'Email parameter tidak ada'}), 400


@app.route('/tambah_ke_keranjang', methods=['POST'])
def tambah_ke_keranjang():
    print("Received data:", request.form.to_dict())  # Log data
    
    product_id = request.form.get('productId')
    product_name = request.form.get('name')
    
    try:
        product_price = float(request.form.get('price', 0))
        quantity = int(request.form.get('quantity', 1))
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid price or quantity'}), 400
    
    if not product_id or not product_name:
        return jsonify({'status': 'error', 'message': 'Product ID or name missing'}), 400
    
    # Initialize the cart if not already set
    cart = session.get('cart', [])
    
    # Check if the product already exists in the cart
    product_in_cart = next((item for item in cart if item['product_id'] == product_id), None)
    if product_in_cart:
        product_in_cart['quantity'] += quantity
    else:
        cart.append({'product_id': product_id, 'quantity': quantity, 'price': product_price, 'name': product_name})
    
    # Save the updated cart to the session
    session['cart'] = cart
    session.modified = True
    
    return jsonify({
        'status': 'success',
        'message': 'Product added to cart successfully',
        'cart': cart
    })


@app.route('/keranjang', methods=['GET'])
def show_keranjang():
    
    if 'email' not in session:
        return redirect(url_for('login'))

    cart = session.get('cart', [])
    email = session['email']
    
    if not cart:
        print('Cart is empty or not retrieved correctly.')
    
    for item in cart:
        if 'price' not in item:
            item['price'] = 0

    total_price = sum(item['price'] * item['quantity'] for item in cart)
    # print("Total Price:", total_price)
    
    user = db.users.find_one({'email': email}, {'_id': 0, 'nama': 1, 'email': 1, 'noHp': 1})
    # print("User Data:", user)
    
    if not user:
        return "User data not found", 404
    
    return render_template('keranjang.html', user=user, keranjang=cart, total_price=total_price)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        email = request.form['email']
        address = request.form['address']  # Corrected field name to 'address'
        cart = session.get('cart', [])

        if not cart:
            return "Cart is empty or not retrieved correctly.", 400
        
        for item in cart:
            if 'price' not in item:
                item['price'] = 0
                
        total_price = sum(item['price'] * item['quantity'] for item in cart)
        user = db.users.find_one({'email': email}, {'_id': 0, 'nama': 1, 'email': 1, 'noHp': 1})
        quantity = item['quantity']
        print(quantity)
        product_name = item['name']
        
        if not user:
            return "User not found.", 404
        
        param = {
            "transaction_details": {
                "order_id": ''.join(random.choices(string.ascii_letters, k=8)),
                "gross_amount": total_price,
            },
            "credit_card": {
                "secure": True
            },
            "customer_details": {
                "first_name": user['nama'],
                "last_name": "",
                "email": email,
                "phone": user['noHp'],
                "billing_address": {
                    "address": address,
                },
            },
        }

        try:
            transaction = snap.create_transaction(param)
            transaction_token = transaction['token']
            session['transaction_token'] = transaction_token
        except Exception as e:
            return f"Transaction creation failed: {str(e)}", 500
        return redirect(url_for('checkout'))
        
    elif request.method == 'GET':
        # Retrieve the transaction token from the session
        transaction_token = session.get('transaction_token')
        cart = session.get('cart', [])
        
        for item in cart:
            if 'price' not in item:
                item['price'] = 0
                
        total_price = sum(item['price'] * item['quantity'] for item in cart)
        
        if not transaction_token:
            return "Transaction token is missing.", 400
        
        return render_template('checkout.html', transaction_token=transaction_token, total_price=total_price, keranjang=cart)

@app.route('/dash',methods=['GET','POST'])
def dash():
    users = list(db.users.find({}, {'_id': 0, 'email': 1, 'nama': 1, 'noHp': 1, 'registration_date': 1}))
    
    produk = list(db.produk.find({}))
    produk_counts = defaultdict(int)
    for produk in produk:
        produk_counts[produk['name']] += 1
        
    makanan = list(db.produk.find({'category': 'Makanan'}))
    makanan_counts = defaultdict(int)
    for item in makanan:
        makanan_counts[item['name']] += 1
        
    minuman = list(db.produk.find({'category': 'Minuman'}))
    minuman_counts = defaultdict(int)
    for item in minuman:
        minuman_counts[item['name']] += 1
    return render_template('dash.html', users=users, produk=produk, produk_counts=produk_counts, 
                        makanan=makanan, makanan_counts=makanan_counts, minuman=minuman, minuman_counts=minuman_counts)

@app.route('/adminProduk',methods=['GET','POST'])
def adminProduk():
    produk = list(db.produk.find({}))
    return render_template('adminProduk.html', produk=produk)

@app.route('/tambah-produk', methods=['POST'])
def tambah_produk():
    try:
        # Ambil data dari request
        name = request.form.get('productName')
        category = request.form.get('productCategory')
        quantity = request.form.get('productQuantity')
        price = request.form.get('productPrice')

        # Validasi data
        if not name or not category or not quantity or not price:
            raise ValueError("Semua field harus diisi.")

        quantity = int(quantity)
        price = float(price)

        # Handling file upload
        filename = None
        if 'produkImage' in request.files:
            file = request.files['produkImage']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Simpan ke database
        new_product = {
            "name": name,
            "category": category,
            "quantity": quantity,
            "price": price,
            "image": filename,
        }
        db.produk.insert_one(new_product)

        return jsonify({"result": "success"})
    
    except ValueError as ve:
        return jsonify({"result": "error", "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"result": "error", "message": str(e)}), 400
    
@app.route('/edit/<produk_id>', methods=['GET', 'POST'])
def edit(produk_id):
    if request.method == 'GET':
        produk = db.produk.find_one({'_id': ObjectId(produk_id)})
        if not produk:
            return 'Product not found', 404
        return render_template('edit.html', produk=produk)
    elif request.method == 'POST':
        try:
            product_name = request.form['productName']
            product_category = request.form['productCategory']
            product_quantity = int(request.form['productQuantity'])
            product_price = float(request.form['productPrice'])

            update_data = {
                'name': product_name,
                'category': product_category,
                'quantity': product_quantity,
                'price': product_price,
            }

            if 'produkImage' in request.files:
                file = request.files['produkImage']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    update_data['image'] = filename
            result = db.produk.update_one({'_id': ObjectId(produk_id)}, {'$set': update_data})

            if result.modified_count == 1:
                return jsonify({'result': 'success', 'msg': 'Produk Makanan berhasil diupdate'})
            return jsonify({'result': 'failure', 'msg': 'Produk produk tidak ditemukan atau update tidak berhasil'})
        except Exception as e:
            return jsonify({'result': 'failure', 'msg': str(e)})
    
@app.route('/delete/<produk_id>', methods=['DELETE'])
def delete(produk_id):
    try:
        result = db.produk.delete_one({'_id': ObjectId(produk_id)})
        if result.deleted_count == 0:
            return jsonify({'result': 'failure', 'msg': 'Produk tidak ditemukan'})
        return jsonify({'result': 'success', 'msg': 'Produk berhasil terhapus'})
    except Exception as e:
        return jsonify({'result': 'failure', 'msg': str(e)})

@app.route('/makanan', methods=['GET', 'POST'])
def makanan():
    makanan = list(db.produk.find({'category': 'Makanan'}))
    return render_template('makanan.html', makanan=makanan)

@app.route('/minuman', methods=['GET', 'POST'])
def minuman():
    minuman = list(db.produk.find({'category': 'Minuman'}))
    return render_template('minuman.html', minuman=minuman)

@app.route('/rokok', methods=['GET', 'POST'])
def rokok():
    rokok = list(db.produk.find({'category': 'Rokok'}))
    return render_template('rokok.html', rokok=rokok)

@app.route('/sabun', methods=['GET', 'POST'])
def sabun():
    sabun = list(db.produk.find({'category': 'Sabun'}))
    return render_template('sabun.html', sabun=sabun)

@app.route('/shampoo', methods=['GET', 'POST'])
def shampoo():
    shampoo = list(db.produk.find({'category': 'Shampoo'}))
    return render_template('shampoo.html', shampoo=shampoo)

@app.route('/detergent', methods=['GET', 'POST'])
def detergent():
    detergent = list(db.produk.find({'category': 'Detergent'}))
    return render_template('detergent.html', detergent=detergent)

@app.route('/user',methods=['GET','POST'])
def user():
    users = list(db.users.find({}, {'_id':0, 'email':1, 'nama':1, 'noHp':1, 'registration_date':1,}))
    return render_template('user.html', users=users)

@app.route('/hapusUser', methods=['POST'])
def hapusUser():
    email = request.json.get('email')
    if email:
        result = db.users.delete_one({'email': email})
        if result.deleted_count == 1:
            return jsonify({'success': True, 'message': 'User berhasil terhapus'}), 200
        else:
            return jsonify({'success': False, 'message': 'Penghapusan user gagal'}), 404
    else:
        return jsonify({'success': False, 'message': 'Email parameter tidak ada'}), 400

@app.route('/logout', methods=['GET'])
def logout():
    # Clear the entire session
    session.clear()

    # Redirect to the home page or another safe page
    return redirect(url_for('home'))

if __name__ == '__main__':
    #DEBUG is SET to TRUE. CHANGE FOR PROD
    app.run('0.0.0.0',port=5000,debug=True)