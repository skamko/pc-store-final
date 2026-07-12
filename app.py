from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pc_store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- FORMS ---
class RegisterForm(FlaskForm):
    username = StringField('მომხმარებელი', validators=[DataRequired(), Length(min=4, max=150)])
    password = PasswordField('პაროლი', validators=[DataRequired(), Length(min=4, max=150)])
    submit = SubmitField('რეგისტრაცია')

class LoginForm(FlaskForm):
    username = StringField('მომხმარებელი', validators=[DataRequired()])
    password = PasswordField('პაროლი', validators=[DataRequired()])
    submit = SubmitField('შესვლა')

class ProductForm(FlaskForm):
    name = StringField('სახელი', validators=[DataRequired()])
    price = FloatField('ფასი', validators=[DataRequired()])
    image_url = StringField('სურათის URL')
    description = TextAreaField('აღწერა')
    submit = SubmitField('დამატება')

# --- ROUTES ---
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    name_lower = product.name.lower()
    
    recommended_gpu = "RTX 4070 Super"
    recommended_cpu = "Ryzen 5 7600"
    target_res = "General Gaming"

    if "ryzen 5" in name_lower or "i5" in name_lower:
        recommended_gpu = "RTX 4070 Super / RX 7800 XT"
        target_res = "1440p (2K) High/Ultra"
    elif "ryzen 7" in name_lower or "i7" in name_lower:
        recommended_gpu = "RTX 4080 Super / RX 7900 XTX"
        target_res = "1440p Esports / 4K Max"
    elif "4060" in name_lower or "6600" in name_lower:
        recommended_cpu = "AMD Ryzen 5 5600 / Intel i3-12100F"
        target_res = "1080p Entry/Medium"
    elif "4080" in name_lower or "4090" in name_lower:
        recommended_cpu = "AMD Ryzen 7 7800X3D"
        target_res = "4K Ultra"

    return render_template('product_detail.html', product=product, recommended_gpu=recommended_gpu, recommended_cpu=recommended_cpu, target_res=target_res)

@app.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('პროდუქტი წარმატებით წაიშალა!', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('ეს მომხმარებელი უკვე არსებობს.', 'danger')
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(form.password.data)
        is_first = User.query.count() == 0
        new_user = User(username=form.username.data, password=hashed_pw, is_admin=is_first)
        db.session.add(new_user)
        db.session.commit()
        flash('რეგისტრაცია წარმატებულია!', 'success')
        return redirect(url_for('login'))
    return render_template('auth.html', form=form, title="რეგისტრაცია")

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        flash('არასწორი მონაცემები.', 'danger')
    return render_template('auth.html', form=form, title="შესვლა")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    form = ProductForm()
    if form.validate_on_submit():
        img = form.image_url.data if form.image_url.data else "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=500"
        new_prod = Product(name=form.name.data, price=form.price.data, image_url=img, description=form.description.data)
        db.session.add(new_prod)
        db.session.commit()
        flash('ნაწილი წარმატებით დაემატა!', 'success')
        return redirect(url_for('index'))
    return render_template('add_product.html', form=form)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
