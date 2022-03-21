import os
from os import abort

from flask import Flask, render_template, send_file, request
from werkzeug.utils import redirect
from data import db_session
from data.doings import Doings
from forms.doings import DoingsForm
from forms.loginform import LoginForm
from forms.user import RegisterForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from data.users import User
from waitress import serve

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


# Главная страница
@app.route('/<category>', methods=['POST', 'GET'])
def index_category(category):
    db_sess = db_session.create_session()
    if current_user.is_authenticated:
        if category == 'home':
            done_doings = db_sess.query(Doings).filter(Doings.user == current_user, Doings.donecheck == True, Doings.doing_category == False)
            not_done_doings = db_sess.query(Doings).filter(Doings.user == current_user, Doings.donecheck == False, Doings.doing_category == False)
            current_category = 'home'
        elif category == 'work':
            done_doings = db_sess.query(Doings).filter(Doings.user == current_user, Doings.donecheck == True, Doings.doing_category == True)
            not_done_doings = db_sess.query(Doings).filter(Doings.user == current_user, Doings.donecheck == False, Doings.doing_category == True)
            current_category = 'work'
        else:
            done_doings = db_sess.query(Doings).filter(Doings.user == current_user, Doings.donecheck == True)
            not_done_doings = db_sess.query(Doings).filter(Doings.user == current_user, Doings.donecheck == False)
            current_category = 'all'
        categories = {'all':'Все дела', 'home': 'Домашние дела', 'work':'Рабочие дела'}
        return render_template("index.html", done_doings=done_doings, not_done_doings=not_done_doings, title='ToDo - список дел',
                               current_category=current_category, categories=categories)
    else:
        return render_template("index.html", title='ToDo - список дел')

@app.route('/', methods=['POST', 'GET'])
def index():
    return redirect('/all')

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.name == form.name.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.name == form.name.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


# Добавление дела
@app.route('/add_doings',  methods=['GET', 'POST'])
@login_required
def add_doings():
    form = DoingsForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        doings = Doings()
        doings.content = form.content.data
        doings.doing_category = bool(int(form.doing_category.data))
        current_user.doings.append(doings)
        db_sess.merge(current_user)
        db_sess.commit()
        return redirect('/')
    return render_template('add_doings.html', form=form, title='Добавить дело')


# Удаление дела
@app.route('/doings_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def doings_delete(id):
    db_sess = db_session.create_session()
    doings = db_sess.query(Doings).filter(Doings.id == id,
                                      Doings.user == current_user
                                      ).first()
    if doings:
        db_sess.delete(doings)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/')


# изменение галочки сделано/не сделано в обе строны
@app.route('/doings_done/<int:id>', methods=['GET', 'POST'])
@login_required
def doings_done(id):
    db_sess = db_session.create_session()
    doings = db_sess.query(Doings).filter(Doings.id == id,
                                      Doings.user == current_user
                                      ).first()
    if doings:
        doings.donecheck = (doings.donecheck + 1) % 2
        db_sess.commit()
    else:
        abort(404)
    return redirect('/')


# экспорт данных в .csv
@app.route('/download/<int:id>', methods=['GET', 'POST'])
@login_required
def download(id):
    db_sess = db_session.create_session()
    path = "tmp/todo.csv"
    file = open(path, 'w')
    doings = db_sess.query(Doings).filter(Doings.user == current_user)
    for do in list(doings):
        file.write(''.join((do.content, ';', str(int(do.donecheck)), ';', category_num_to_work(do.donecheck),'\n')))
    file.close()
    return send_file(path, as_attachment=True)


# импорт данных
@app.route('/import/<int:id>', methods=['POST', 'GET'])
@login_required
def upload(id):
    deals = []
    if request.method == 'POST':
        result = request.files['myfile']
        for doing in list(result):
            if not correct_string(doing.decode("utf-8", "ignore").strip()):
                return render_template("error_import.html", title='Ошибка импорта')
            deals.append(doing.decode("utf-8", "ignore").strip().split(';'))
    else:
        pass
    for deal in deals:
        db_sess = db_session.create_session()
        doings = Doings()
        doings.content = deal[0]
        doings.donecheck = int(deal[1])
        if deal[2] == 'home':
            doings.doing_category = 0
        else:
            doings.doing_category = 1
        current_user.doings.append(doings)
        db_sess.merge(current_user)
        db_sess.commit()

    return redirect('/')


def category_num_to_work(n):
    if n == 0:
        return 'home'
    return 'work'

# Проверка данных на корректность для импорта
def correct_string(s):
    if (len(s) > 7) and (s[-5] == s[-7] == ';') and (s[-6] in {'1', '0'}) and \
            (s[-4:] == 'work' or s[-4:] == 'home'):
        return True
    return False


@app.route('/lk', methods=['POST', 'GET'])
@ login_required
def lk():
    db_sess = db_session.create_session()
    done_amount = len(list(db_sess.query(Doings).filter(Doings.user == current_user, Doings.donecheck == True)))
    note_done_amount = len(list(db_sess.query(Doings).filter(Doings.user == current_user, Doings.donecheck == False)))
    all_amount = done_amount + note_done_amount
    if all_amount == 0:
        message = 'Добавьте дела и приступайте к работе'
    elif done_amount / all_amount < 0.4:
        message = 'Сделано мало, пора работать'
    elif done_amount / all_amount < 0.8:
        message = 'Неплохо, но можно и лучше'
    else:
        message = 'Вы молодец!'
    return render_template("lk.html", done_amount=done_amount, note_done_amount=note_done_amount, all_amount=all_amount,
                           title='Статистика', message=message)


"""if __name__ == '__main__':
   db_session.global_init("db/doings.db")
   app.run(host='127.0.0.1', port=8000, debug=True)"""

if __name__ == '__main__':
    db_session.global_init("db/doings.db")
    port = int(os.environ.get("PORT", 5000))
    serve(app, host='0.0.0.0', port=port)