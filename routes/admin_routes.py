from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import db
from database.models.user import User
from database.models.job import Job
from database.models.company import Company
from database.models.application import Application
from database.models.resume import Resume
from database.models.notification import Notification

admin_bp = Blueprint('admin', __name__)


def require_admin():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return None, jsonify({'error': 'Доступ запрещён. Требуются права администратора'}), 403
    return user, None, None


@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_admin_stats():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Доступ запрещён'}), 403

        stats = {
            'users': {
                'total': User.query.count(),
                'jobseekers': User.query.filter_by(role='jobseeker').count(),
                'employers': User.query.filter_by(role='employer').count(),
                'admins': User.query.filter_by(role='admin').count(),
                'active': User.query.filter_by(is_active=True).count(),
            },
            'jobs': {
                'total': Job.query.count(),
                'active': Job.query.filter_by(is_active=True).count(),
                'hot': Job.query.filter_by(is_hot=True).count(),
            },
            'companies': {
                'total': Company.query.count(),
                'verified': Company.query.filter_by(is_verified=True).count(),
                'active': Company.query.filter_by(is_active=True).count(),
            },
            'resumes': {
                'total': Resume.query.count(),
                'active': Resume.query.filter_by(is_active=True).count(),
                'public': Resume.query.filter_by(is_public=True).count(),
            },
            'applications': {
                'total': Application.query.count(),
                'pending': Application.query.filter_by(status='pending').count(),
                'invited': Application.query.filter_by(status='invited').count(),
                'rejected': Application.query.filter_by(status='rejected').count(),
            },
        }

        return jsonify({'stats': stats}), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Доступ запрещён'}), 403

        page = request.args.get('page', 1, type=int)
        search = request.args.get('q', '').strip()
        role = request.args.get('role', '').strip()

        query = User.query
        if search:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    User.name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                )
            )
        if role:
            query = query.filter_by(role=role)

        query = query.order_by(User.created_at.desc())
        paginated = query.paginate(page=page, per_page=20, error_out=False)

        return jsonify({
            'users': [u.to_dict(include_private=True) for u in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@admin_bp.route('/users/<int:target_id>/toggle-active', methods=['PUT'])
@jwt_required()
def toggle_user_active(target_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Доступ запрещён'}), 403

        target = User.query.get(target_id)
        if not target:
            return jsonify({'error': 'Пользователь не найден'}), 404

        target.is_active = not target.is_active
        db.session.commit()

        return jsonify({
            'message': f'Пользователь {"активирован" if target.is_active else "заблокирован"}',
            'user': target.to_dict(include_private=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера'}), 500


@admin_bp.route('/companies/<int:company_id>/verify', methods=['PUT'])
@jwt_required()
def verify_company(company_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Доступ запрещён'}), 403

        company = Company.query.get(company_id)
        if not company:
            return jsonify({'error': 'Компания не найдена'}), 404

        company.is_verified = not company.is_verified
        db.session.commit()

        if company.is_verified and company.owner_id:
            Notification.create_notification(
                user_id=company.owner_id,
                title='Компания верифицирована',
                text=f'Ваша компания «{company.name}» успешно верифицирована.',
                type='system',
            )
            db.session.commit()

        return jsonify({
            'message': f'Компания {"верифицирована" if company.is_verified else "деверифицирована"}',
            'company': company.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера'}), 500


@admin_bp.route('/jobs/<int:job_id>/toggle-hot', methods=['PUT'])
@jwt_required()
def toggle_job_hot(job_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Доступ запрещён'}), 403

        job = Job.query.get(job_id)
        if not job:
            return jsonify({'error': 'Вакансия не найдена'}), 404

        job.is_hot = not job.is_hot
        db.session.commit()

        return jsonify({
            'message': f'Вакансия {"помечена как горячая" if job.is_hot else "снята с горячих"}',
            'job': job.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера'}), 500


@admin_bp.route('/notifications/broadcast', methods=['POST'])
@jwt_required()
def broadcast_notification():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Доступ запрещён'}), 403

        data = request.get_json()
        title = data.get('title', '').strip()
        text = data.get('text', '').strip()
        role = data.get('role', '')

        if not title or not text:
            return jsonify({'error': 'Заголовок и текст обязательны'}), 400

        query = User.query.filter_by(is_active=True)
        if role:
            query = query.filter_by(role=role)

        users = query.all()
        count = 0

        for u in users:
            Notification.create_notification(
                user_id=u.id,
                title=title,
                text=text,
                type='system',
            )
            count += 1

        db.session.commit()

        return jsonify({
            'message': f'Уведомление отправлено {count} пользователям',
            'count': count,
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500