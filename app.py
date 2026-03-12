import os
from flask import Flask, render_template, send_from_directory, jsonify
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from config import config
from database.db import db

bcrypt = Bcrypt()
jwt = JWTManager()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=['http://localhost:5000', 'http://127.0.0.1:5000'],
         supports_credentials=True)

    # Create required folders
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'avatars'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'logos'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'database'), exist_ok=True)

    # Register blueprints
    from routes.auth_routes import auth_bp
    from routes.job_routes import job_bp
    from routes.company_routes import company_bp
    from routes.resume_routes import resume_bp
    from routes.application_routes import application_bp
    from routes.message_routes import message_bp
    from routes.admin_routes import admin_bp
    from routes.page_routes import page_bp
    from routes.notification_routes import notification_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(job_bp, url_prefix='/api/jobs')
    app.register_blueprint(company_bp, url_prefix='/api/companies')
    app.register_blueprint(resume_bp, url_prefix='/api/resumes')
    app.register_blueprint(application_bp, url_prefix='/api/applications')
    app.register_blueprint(message_bp, url_prefix='/api/messages')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(notification_bp, url_prefix='/api/auth')
    app.register_blueprint(page_bp)

    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Токен истёк',
            'code': 'TOKEN_EXPIRED'
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'error': 'Недействительный токен',
            'code': 'INVALID_TOKEN'
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'error': 'Токен не предоставлен',
            'code': 'MISSING_TOKEN'
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Токен отозван',
            'code': 'TOKEN_REVOKED'
        }), 401

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        if _is_api_request():
            return jsonify({'error': 'Ресурс не найден'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        if _is_api_request():
            return jsonify({'error': 'Внутренняя ошибка сервера'}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        if _is_api_request():
            return jsonify({'error': 'Доступ запрещён'}), 403
        return render_template('errors/404.html'), 403

    # Static uploads route
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Health check
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'ok',
            'app': app.config['APP_NAME'],
            'version': app.config['APP_VERSION'],
        }), 200

    # Create DB and seed data
    with app.app_context():
        # Import all models
        from database.models import (
            User, Job, Company, Resume, Application,
            Message, Conversation, Notification, Category,
            Experience, Education, Language
        )
        db.create_all()
        _seed_initial_data()

    return app


def _is_api_request():
    from flask import request
    return request.path.startswith('/api/')


def _seed_initial_data():
    from database.models.category import Category
    from database.db import db

    if Category.query.count() == 0:
        categories = [
            Category(name='Информационные технологии', icon='it', slug='it',
                     description='Разработка, IT-инфраструктура, безопасность'),
            Category(name='Финансы и бухгалтерия', icon='finance', slug='finance',
                     description='Бухгалтеры, финансисты, аналитики'),
            Category(name='Строительство и архитектура', icon='construction', slug='construction',
                     description='Инженеры, архитекторы, прорабы'),
            Category(name='Медицина и фармацевтика', icon='medicine', slug='medicine',
                     description='Врачи, медсёстры, фармацевты'),
            Category(name='Образование и наука', icon='education', slug='education',
                     description='Учителя, преподаватели, исследователи'),
            Category(name='Маркетинг и реклама', icon='marketing', slug='marketing',
                     description='Маркетологи, дизайнеры, SMM'),
            Category(name='Юриспруденция', icon='law', slug='law',
                     description='Юристы, адвокаты, нотариусы'),
            Category(name='Производство и промышленность', icon='industry', slug='industry',
                     description='Технологи, операторы, механики'),
            Category(name='Транспорт и логистика', icon='transport', slug='transport',
                     description='Водители, логисты, экспедиторы'),
            Category(name='Торговля и продажи', icon='sales', slug='sales',
                     description='Менеджеры по продажам, торговые представители'),
            Category(name='Нефть и газ', icon='oil', slug='oil-gas',
                     description='Инженеры нефтяники, геологи, операторы'),
            Category(name='Государственное управление', icon='government', slug='government',
                     description='Государственные служащие, чиновники'),
        ]
        db.session.bulk_save_objects(categories)
        db.session.commit()


if __name__ == '__main__':
    app = create_app('development')
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        use_reloader=True,
    )