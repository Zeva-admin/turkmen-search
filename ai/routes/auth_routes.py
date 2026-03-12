from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, unset_jwt_cookies
)
from database.db import db
from database.models.user import User
from database.models.notification import Notification

auth_bp = Blueprint('auth', __name__)


def validate_email(email):
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    return len(password) >= 6


@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        role = data.get('role', 'jobseeker')

        # Validation
        errors = {}
        if not name or len(name) < 2:
            errors['name'] = 'Имя должно содержать минимум 2 символа'
        if not email or not validate_email(email):
            errors['email'] = 'Введите корректный email адрес'
        if not password or not validate_password(password):
            errors['password'] = 'Пароль должен содержать минимум 6 символов'
        if role not in ['jobseeker', 'employer']:
            errors['role'] = 'Некорректная роль'

        if errors:
            return jsonify({'error': 'Ошибка валидации', 'fields': errors}), 422

        # Check existing user
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Пользователь с таким email уже существует'}), 409

        # Create user
        user = User(
            name=name,
            email=email,
            role=role,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Welcome notification
        Notification.create_notification(
            user_id=user.id,
            title='Добро пожаловать в Turkmen Search!',
            text=f'Рады видеть вас на платформе, {name}. Начните поиск работы или разместите вакансию.',
            type='system',
            link='/',
            link_text='На главную',
        )
        db.session.commit()

        # Generate tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'message': 'Регистрация успешна',
            'user': user.to_dict(include_private=True),
            'access_token': access_token,
            'refresh_token': refresh_token,
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email и пароль обязательны'}), 400

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Неверный email или пароль'}), 401

        if not user.is_active:
            return jsonify({'error': 'Аккаунт заблокирован. Обратитесь в поддержку'}), 403

        # Update last seen
        user.last_seen = datetime.utcnow()
        db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return jsonify({
            'message': 'Вход выполнен успешно',
            'user': user.to_dict(include_private=True),
            'access_token': access_token,
            'refresh_token': refresh_token,
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        identity = get_jwt_identity()
        access_token = create_access_token(identity=identity)
        return jsonify({'access_token': access_token}), 200
    except Exception as e:
        return jsonify({'error': 'Ошибка обновления токена'}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        user.last_seen = datetime.utcnow()
        db.session.commit()

        return jsonify({'user': user.to_dict(include_private=True)}), 200
    except Exception as e:
        return jsonify({'error': 'Ошибка сервера'}), 500


@auth_bp.route('/update-profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        allowed_fields = ['name', 'phone', 'city', 'about', 'gender']
        for field in allowed_fields:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    value = value.strip()
                setattr(user, field, value)

        if 'birth_date' in data and data['birth_date']:
            try:
                user.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Неверный формат даты'}), 400

        if 'current_password' in data and 'new_password' in data:
            if not user.check_password(data['current_password']):
                return jsonify({'error': 'Текущий пароль неверен'}), 400
            if not validate_password(data['new_password']):
                return jsonify({'error': 'Новый пароль слишком короткий'}), 400
            user.set_password(data['new_password'])

        user.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Профиль обновлён',
            'user': user.to_dict(include_private=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'message': 'Выход выполнен'}), 200


@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    exists = User.query.filter_by(email=email).first() is not None
    return jsonify({'exists': exists}), 200