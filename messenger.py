import os
import sqlite3

from flask import Flask, jsonify, make_response, redirect, render_template, request, session, url_for

import settings

app = Flask(__name__)
app.config.from_object(settings)


def _get_message(id=None):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        c = conn.cursor()

        if id:
            id = int(id)
            q = "SELECT * FROM messages WHERE id=? ORDER BY dt DESC"
            rows = c.execute(q, (id,))

        else:
            q = "SELECT * FROM messages ORDER BY dt DESC"
            rows = c.execute(q)

        return [{'id': r[0], 'dt': r[1], 'message': r[2], 'sender': r[3]} for r in rows]


def _add_message(message, sender):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        c = conn.cursor()
        q = "INSERT INTO messages VALUES (NULL, datetime('now', 'localtime'),?,?)"
        c.execute(q, (message, sender))
        conn.commit()
        return c.lastrowid


def _delete_message(ids):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        c = conn.cursor()
        q = "DELETE FROM messages WHERE id=?"

        try:
            for i in ids:
                c.execute(q, (int(i),))
        except TypeError:
            c.execute(q, (int(ids),))

        conn.commit()


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        _add_message(request.form['message'], request.form['username'])
        redirect(url_for('home'))

    return render_template('index.html', messages=_get_message())


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not 'logged_in' in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        _delete_message([k[6:] for k in request.form.keys()])
        redirect(url_for('admin'))

    messages = _get_message()
    messages.reverse()

    return render_template('admin.html', messages=messages)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME'] or request.form['password'] != app.config['PASSWORD']:
            error = 'Неверное имя пользователя/пароль'
        else:
            session['logged_in'] = True
            return redirect(url_for('admin'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))


@app.route('/messages/api', methods=['GET'])
@app.route('/messages/api/<int:id>', methods=['GET'])
def get_message_by_id(id=None):
    messages = _get_message(id)
    if not messages:
        return make_response(jsonify({'ошибка': 'Нету'}), 404)

    return jsonify({'messages': messages})


@app.route('/messages/api', methods=['POST'])
def create_message():
    if not request.json or not 'message' in request.json or not 'sender' in request.json:
        return make_response(jsonify({'ошибка': 'Запрос необработан'}), 400)

    id = _add_message(request.json['message'], request.json['sender'])

    return get_message_by_id(id), 201


@app.route('/messages/api/<int:id>', methods=['DELETE'])
def delete_message_by_id(id):
    _delete_message(id)
    return jsonify({'result': True})


if __name__ == '__main__':

    # Создает БД, если её нет
    if not os.path.exists(app.config['DATABASE']):
        try:
            conn = sqlite3.connect(app.config['DATABASE'])
            sql_path = os.path.join(app.config['APP_ROOT'], 'db_init.sql')
            cmd = open(sql_path, 'r').read()
            c = conn.cursor()
            c.execute(cmd)
            conn.commit()
            conn.close()
        except IOError:
            print("Не выполнено, выходжу...")
            raise
        except sqlite3.OperationalError:
            print("Не выполнено, выходжу...")
            raise

    app.run(host='0.0.0.0')
