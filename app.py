from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
import os

# --- Configuración de la Aplicación ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'una-clave-secreta-muy-dificil-de-adivinar'
# Obtener la ruta absoluta del directorio del proyecto
basedir = os.path.abspath(os.path.dirname(__file__))
# Configurar la URI de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redirige a la página de login si no está autenticado

# --- Modelos de la Base de Datos ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'stock': self.stock,
            'category': self.category
        }

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# --- Formularios ---
class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    password2 = PasswordField(
        'Repetir Contraseña', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrarse')

# --- Rutas de la Aplicación ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuario o contraseña inválidos')
            return redirect(url_for('login'))
        login_user(user, remember=True)
        return redirect(url_for('chat'))
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('¡Felicidades, ahora eres un usuario registrado!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/')
@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# --- API para el Chat ---
from services import get_ai_response

@app.route('/api/chat', methods=['POST'])
#@login_required
def api_chat():
    data = request.json
    message = data.get('message')
    if not message:
        return jsonify({'error': 'No se proporcionó ningún mensaje'}), 400
    
    response = get_ai_response(message)
    return jsonify({'reply': response})

# --- API para obtener productos (opcional, para debugging) ---
@app.route('/api/products', methods=['GET'])
@login_required
def api_products():
    products = Product.query.all()
    return jsonify([product.to_dict() for product in products])


if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Crea la base de datos y las tablas si no existen
        
        # Insertar productos de ejemplo si no existen
        if Product.query.count() == 0:
            productos_ejemplo = [
                Product(name='Producto A', description='Descripción del producto A', price=29.99, stock=50, category='Electrónicos'),
                Product(name='Producto B', description='Descripción del producto B', price=19.99, stock=30, category='Ropa'),
                Product(name='Producto C', description='Descripción del producto C', price=39.99, stock=0, category='Hogar'),
                Product(name='Laptop HP', description='Laptop HP Pavilion 15"', price=799.99, stock=5, category='Electrónicos'),
                Product(name='Mouse Inalámbrico', description='Mouse óptico inalámbrico', price=25.50, stock=100, category='Accesorios'),
            ]
            
            for producto in productos_ejemplo:
                db.session.add(producto)
            db.session.commit()
            print("Productos de ejemplo insertados en la base de datos.")
            
    app.run(debug=True, port=5000)