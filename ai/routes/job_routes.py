from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from sqlalchemy import or_, and_
from database.db import db
from database.models.job import Job
from database.models.company import Company
from database.models.user import User
from database.models.application import Application

job_bp = Blueprint('jobs', __name__)

CITIES = [
    'Ашхабад', 'Туркменабат', 'Дашогуз',
    'Мары', 'Балканабат', 'Туркменбаши'
]


@job_bp.route('', methods=['GET'])
def get_jobs():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 50)

        query = Job.query.filter_by(is_active=True)

        # Filters
        search = request.args.get('q', '').strip()
        if search:
            query = query.filter(
                or_(
                    Job.title.ilike(f'%{search}%'),
                    Job.description.ilike(f'%{search}%'),
                )
            )

        city = request.args.get('city', '').strip()
        if city:
            query = query.filter(Job.city == city)

        employment_type = request.args.get('employment_type', '').strip()
        if employment_type:
            query = query.filter(Job.employment_type == employment_type)

        experience = request.args.get('experience', '').strip()
        if experience:
            query = query.filter(Job.experience == experience)

        salary_from = request.args.get('salary_from', type=int)
        if salary_from:
            query = query.filter(
                or_(Job.salary_from >= salary_from, Job.salary_negotiable == True)
            )

        salary_to = request.args.get('salary_to', type=int)
        if salary_to:
            query = query.filter(
                or_(Job.salary_to <= salary_to, Job.salary_negotiable == True)
            )

        category_id = request.args.get('category_id', type=int)
        if category_id:
            query = query.filter(Job.category_id == category_id)

        remote = request.args.get('remote', type=bool)
        if remote:
            query = query.filter(Job.remote == True)

        is_hot = request.args.get('is_hot', '').strip()
        if is_hot == 'true':
            query = query.filter(Job.is_hot == True)

        # Sorting
        sort = request.args.get('sort', 'date')
        if sort == 'salary':
            query = query.order_by(Job.salary_from.desc().nullslast())
        elif sort == 'views':
            query = query.order_by(Job.views_count.desc())
        else:
            query = query.order_by(Job.created_at.desc())

        # Hot jobs first
        query = query.order_by(Job.is_hot.desc())

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'jobs': [job.to_dict() for job in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': paginated.has_next,
            'has_prev': paginated.has_prev,
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@job_bp.route('/<int:job_id>', methods=['GET'])
def get_job(job_id):
    try:
        job = Job.query.get(job_id)
        if not job:
            return jsonify({'error': 'Вакансия не найдена'}), 404

        # Increment views
        job.views_count += 1
        db.session.commit()

        # Check if user already applied
        already_applied = False
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            if user_id:
                already_applied = Application.query.filter_by(
                    job_id=job_id,
                    user_id=int(user_id)
                ).first() is not None
        except Exception:
            pass

        job_data = job.to_dict(full=True)
        job_data['already_applied'] = already_applied

        # Related jobs
        related = Job.query.filter(
            and_(
                Job.id != job_id,
                Job.is_active == True,
                or_(
                    Job.category_id == job.category_id,
                    Job.city == job.city,
                )
            )
        ).limit(4).all()

        job_data['related_jobs'] = [j.to_dict() for j in related]

        return jsonify({'job': job_data}), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@job_bp.route('', methods=['POST'])
@jwt_required()
def create_job():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user or user.role not in ['employer', 'admin']:
            return jsonify({'error': 'Только работодатели могут создавать вакансии'}), 403

        company = Company.query.filter_by(owner_id=user_id).first()
        if not company and user.role != 'admin':
            return jsonify({'error': 'Сначала создайте компанию'}), 400

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        errors = {}
        if not data.get('title', '').strip():
            errors['title'] = 'Название вакансии обязательно'
        if not data.get('description', '').strip():
            errors['description'] = 'Описание обязательно'
        if not data.get('city', '').strip():
            errors['city'] = 'Город обязателен'
        if data.get('city') and data['city'] not in CITIES:
            errors['city'] = 'Выберите город из списка'

        if errors:
            return jsonify({'error': 'Ошибка валидации', 'fields': errors}), 422

        import json
        skills = data.get('skills', [])
        if isinstance(skills, list):
            skills = json.dumps(skills, ensure_ascii=False)

        job = Job(
            title=data['title'].strip(),
            description=data['description'].strip(),
            requirements=data.get('requirements', '').strip(),
            responsibilities=data.get('responsibilities', '').strip(),
            conditions=data.get('conditions', '').strip(),
            salary_from=data.get('salary_from'),
            salary_to=data.get('salary_to'),
            salary_currency=data.get('salary_currency', 'TMT'),
            salary_negotiable=data.get('salary_negotiable', False),
            city=data['city'],
            address=data.get('address', '').strip(),
            remote=data.get('remote', False),
            employment_type=data.get('employment_type', 'full_time'),
            schedule=data.get('schedule', ''),
            experience=data.get('experience', ''),
            education=data.get('education', ''),
            skills=skills,
            company_id=company.id if company else data.get('company_id'),
            category_id=data.get('category_id'),
        )

        db.session.add(job)
        db.session.commit()

        return jsonify({
            'message': 'Вакансия создана успешно',
            'job': job.to_dict(full=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@job_bp.route('/<int:job_id>', methods=['PUT'])
@jwt_required()
def update_job(job_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        job = Job.query.get(job_id)

        if not job:
            return jsonify({'error': 'Вакансия не найдена'}), 404

        if user.role != 'admin' and job.company.owner_id != user_id:
            return jsonify({'error': 'Нет прав для редактирования'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        updatable = [
            'title', 'description', 'requirements', 'responsibilities',
            'conditions', 'salary_from', 'salary_to', 'salary_currency',
            'salary_negotiable', 'city', 'address', 'remote',
            'employment_type', 'schedule', 'experience', 'education',
            'is_active', 'is_hot', 'category_id'
        ]

        for field in updatable:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    value = value.strip()
                setattr(job, field, value)

        if 'skills' in data:
            import json
            skills = data['skills']
            if isinstance(skills, list):
                skills = json.dumps(skills, ensure_ascii=False)
            job.skills = skills

        job.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Вакансия обновлена',
            'job': job.to_dict(full=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@job_bp.route('/<int:job_id>', methods=['DELETE'])
@jwt_required()
def delete_job(job_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        job = Job.query.get(job_id)

        if not job:
            return jsonify({'error': 'Вакансия не найдена'}), 404

        if user.role != 'admin' and job.company.owner_id != user_id:
            return jsonify({'error': 'Нет прав для удаления'}), 403

        db.session.delete(job)
        db.session.commit()

        return jsonify({'message': 'Вакансия удалена'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@job_bp.route('/stats/overview', methods=['GET'])
def get_stats():
    try:
        from database.models.company import Company
        from database.models.resume import Resume

        total_jobs = Job.query.filter_by(is_active=True).count()
        total_companies = Company.query.filter_by(is_active=True).count()
        total_resumes = Resume.query.filter_by(is_active=True).count()
        total_users = User.query.filter_by(is_active=True).count()

        cities_stats = []
        for city in CITIES:
            count = Job.query.filter_by(city=city, is_active=True).count()
            if count > 0:
                cities_stats.append({'city': city, 'count': count})

        return jsonify({
            'total_jobs': total_jobs,
            'total_companies': total_companies,
            'total_resumes': total_resumes,
            'total_users': total_users,
            'cities': cities_stats,
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера'}), 500


@job_bp.route('/employer/my-jobs', methods=['GET'])
@jwt_required()
def get_my_jobs():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user or user.role not in ['employer', 'admin']:
            return jsonify({'error': 'Доступ запрещён'}), 403

        company = Company.query.filter_by(owner_id=user_id).first()
        if not company:
            return jsonify({'jobs': [], 'total': 0}), 200

        page = request.args.get('page', 1, type=int)
        status = request.args.get('status', '')

        query = Job.query.filter_by(company_id=company.id)
        if status == 'active':
            query = query.filter_by(is_active=True)
        elif status == 'inactive':
            query = query.filter_by(is_active=False)

        query = query.order_by(Job.created_at.desc())
        paginated = query.paginate(page=page, per_page=20, error_out=False)

        return jsonify({
            'jobs': [job.to_dict() for job in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500