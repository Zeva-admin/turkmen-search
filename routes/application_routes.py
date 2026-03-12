from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import db
from database.models.application import Application
from database.models.job import Job
from database.models.user import User
from database.models.company import Company
from database.models.notification import Notification

application_bp = Blueprint('applications', __name__)


@application_bp.route('', methods=['POST'])
@jwt_required()
def create_application():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        if user.role == 'employer':
            return jsonify({'error': 'Работодатели не могут откликаться на вакансии'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        job_id = data.get('job_id')
        if not job_id:
            return jsonify({'error': 'ID вакансии обязателен'}), 400

        job = Job.query.get(job_id)
        if not job or not job.is_active:
            return jsonify({'error': 'Вакансия не найдена или неактивна'}), 404

        existing = Application.query.filter_by(
            job_id=job_id,
            user_id=user_id
        ).first()

        if existing:
            return jsonify({'error': 'Вы уже откликались на эту вакансию'}), 409

        application = Application(
            job_id=job_id,
            user_id=user_id,
            resume_id=data.get('resume_id'),
            cover_letter=data.get('cover_letter', '').strip(),
            status='pending',
        )

        db.session.add(application)

        job.applications_count += 1

        # Notify employer
        company = job.company
        if company and company.owner_id:
            Notification.create_notification(
                user_id=company.owner_id,
                title='Новый отклик на вакансию',
                text=f'{user.name} откликнулся на вакансию «{job.title}»',
                type='application',
                link=f'/dashboard',
                link_text='Просмотреть отклики',
            )

        db.session.commit()

        return jsonify({
            'message': 'Отклик отправлен успешно',
            'application': application.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@application_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_applications():
    try:
        user_id = int(get_jwt_identity())
        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', '').strip()

        query = Application.query.filter_by(user_id=user_id)

        if status:
            query = query.filter_by(status=status)

        query = query.order_by(Application.created_at.desc())
        paginated = query.paginate(page=page, per_page=20, error_out=False)

        return jsonify({
            'applications': [a.to_dict(include_user=False) for a in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@application_bp.route('/job/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job_applications(job_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        job = Job.query.get(job_id)
        if not job:
            return jsonify({'error': 'Вакансия не найдена'}), 404

        if user.role != 'admin' and job.company.owner_id != user_id:
            return jsonify({'error': 'Нет прав для просмотра'}), 403

        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', '').strip()

        query = Application.query.filter_by(job_id=job_id)
        if status:
            query = query.filter_by(status=status)

        query = query.order_by(Application.created_at.desc())
        paginated = query.paginate(page=page, per_page=20, error_out=False)

        applications = []
        for app in paginated.items:
            app_data = app.to_dict(include_job=False)
            if not app.viewed_at:
                app.viewed_at = datetime.utcnow()
                if app.status == 'pending':
                    app.status = 'viewed'
            applications.append(app_data)

        db.session.commit()

        return jsonify({
            'applications': applications,
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@application_bp.route('/<int:app_id>/status', methods=['PUT'])
@jwt_required()
def update_status(app_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        application = Application.query.get(app_id)
        if not application:
            return jsonify({'error': 'Отклик не найден'}), 404

        job = application.job
        if user.role != 'admin' and job.company.owner_id != user_id:
            return jsonify({'error': 'Нет прав для изменения статуса'}), 403

        data = request.get_json()
        new_status = data.get('status')

        valid_statuses = ['pending', 'viewed', 'invited', 'rejected', 'accepted']
        if new_status not in valid_statuses:
            return jsonify({'error': 'Некорректный статус'}), 400

        old_status = application.status
        application.status = new_status
        application.employer_note = data.get('employer_note', application.employer_note)
        application.updated_at = datetime.utcnow()

        # Notify applicant
        status_messages = {
            'invited': f'Вас пригласили на собеседование по вакансии «{job.title}»',
            'rejected': f'К сожалению, по вакансии «{job.title}» получен отказ',
            'accepted': f'Поздравляем! Ваш отклик на вакансию «{job.title}» принят',
        }

        if new_status in status_messages and old_status != new_status:
            Notification.create_notification(
                user_id=application.user_id,
                title='Обновление статуса отклика',
                text=status_messages[new_status],
                type='invitation' if new_status == 'invited' else 'application',
                link='/dashboard',
                link_text='Мои отклики',
            )

        db.session.commit()

        return jsonify({
            'message': 'Статус обновлён',
            'application': application.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@application_bp.route('/employer/all', methods=['GET'])
@jwt_required()
def get_employer_applications():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user or user.role not in ['employer', 'admin']:
            return jsonify({'error': 'Доступ запрещён'}), 403

        company = Company.query.filter_by(owner_id=user_id).first()
        if not company:
            return jsonify({'applications': [], 'total': 0}), 200

        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', '').strip()

        company_job_ids = [j.id for j in company.jobs]

        query = Application.query.filter(
            Application.job_id.in_(company_job_ids)
        )

        if status:
            query = query.filter_by(status=status)

        query = query.order_by(Application.created_at.desc())
        paginated = query.paginate(page=page, per_page=20, error_out=False)

        return jsonify({
            'applications': [a.to_dict() for a in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500