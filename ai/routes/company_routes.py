from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import db
from database.models.company import Company
from database.models.user import User
from database.models.job import Job
from database.models.category import Category
import re

company_bp = Blueprint('companies', __name__)


def slugify(text):
    import unicodedata
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text or 'company'


@company_bp.route('', methods=['GET'])
def get_companies():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 16, type=int)
        per_page = min(per_page, 50)

        query = Company.query.filter_by(is_active=True)

        search = request.args.get('q', '').strip()
        if search:
            query = query.filter(Company.name.ilike(f'%{search}%'))

        city = request.args.get('city', '').strip()
        if city:
            query = query.filter(Company.city == city)

        industry = request.args.get('industry', '').strip()
        if industry:
            query = query.filter(Company.industry == industry)

        company_type = request.args.get('type', '').strip()
        if company_type:
            query = query.filter(Company.company_type == company_type)

        sort = request.args.get('sort', 'name')
        if sort == 'rating':
            query = query.order_by(Company.rating.desc())
        elif sort == 'jobs':
            query = query.order_by(Company.created_at.desc())
        else:
            query = query.order_by(Company.name.asc())

        query = query.order_by(Company.is_verified.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'companies': [c.to_dict() for c in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': paginated.has_next,
            'has_prev': paginated.has_prev,
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@company_bp.route('/categories', methods=['GET'])
def get_categories():
    try:
        categories = Category.query.all()
        return jsonify({
            'categories': [c.to_dict() for c in categories],
            'total': len(categories),
        }), 200
    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@company_bp.route('/<int:company_id>', methods=['GET'])
def get_company(company_id):
    try:
        company = Company.query.get(company_id)
        if not company or not company.is_active:
            return jsonify({'error': 'Компания не найдена'}), 404

        company_data = company.to_dict(full=True)

        page = request.args.get('page', 1, type=int)
        jobs = Job.query.filter_by(
            company_id=company_id,
            is_active=True
        ).order_by(
            Job.is_hot.desc(),
            Job.created_at.desc()
        ).paginate(page=page, per_page=10, error_out=False)

        company_data['jobs'] = [j.to_dict() for j in jobs.items]
        company_data['jobs_total'] = jobs.total
        company_data['jobs_pages'] = jobs.pages

        return jsonify({'company': company_data}), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@company_bp.route('', methods=['POST'])
@jwt_required()
def create_company():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user or user.role not in ['employer', 'admin', 'jobseeker']:
            return jsonify({'error': 'Доступ запрещён'}), 403

        existing = Company.query.filter_by(owner_id=user_id).first()
        if existing and user.role != 'admin':
            return jsonify({
                'error': 'У вас уже есть компания',
                'company': existing.to_dict()
            }), 409

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        errors = {}
        if not data.get('name', '').strip():
            errors['name'] = 'Название компании обязательно'
        if errors:
            return jsonify({'error': 'Ошибка валидации', 'fields': errors}), 422

        name = data['name'].strip()
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while Company.query.filter_by(slug=slug).first():
            slug = f'{base_slug}-{counter}'
            counter += 1

        company = Company(
            name=name,
            slug=slug,
            description=data.get('description', '').strip(),
            short_description=data.get('short_description', '').strip(),
            industry=data.get('industry', '').strip(),
            company_type=data.get('company_type', ''),
            employees_count=data.get('employees_count', ''),
            founded_year=data.get('founded_year'),
            website=data.get('website', '').strip(),
            city=data.get('city', '').strip(),
            address=data.get('address', '').strip(),
            phone=data.get('phone', '').strip(),
            email=data.get('email', '').strip(),
            owner_id=user_id,
        )

        db.session.add(company)
        db.session.flush()

        # Upgrade user to employer
        if user.role != 'admin':
            user.role = 'employer'

        db.session.commit()

        return jsonify({
            'message': 'Компания создана успешно',
            'company': company.to_dict(full=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@company_bp.route('/<int:company_id>', methods=['PUT'])
@jwt_required()
def update_company(company_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        company = Company.query.get(company_id)

        if not company:
            return jsonify({'error': 'Компания не найдена'}), 404

        if user.role != 'admin' and company.owner_id != user_id:
            return jsonify({'error': 'Нет прав для редактирования'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        updatable = [
            'name', 'description', 'short_description', 'industry',
            'company_type', 'employees_count', 'founded_year',
            'website', 'city', 'address', 'phone', 'email'
        ]

        for field in updatable:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    value = value.strip()
                setattr(company, field, value)

        company.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Компания обновлена',
            'company': company.to_dict(full=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@company_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_company():
    try:
        user_id = int(get_jwt_identity())
        company = Company.query.filter_by(owner_id=user_id).first()

        if not company:
            return jsonify({'company': None}), 200

        return jsonify({'company': company.to_dict(full=True)}), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@company_bp.route('/<int:company_id>', methods=['DELETE'])
@jwt_required()
def delete_company(company_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        company = Company.query.get(company_id)

        if not company:
            return jsonify({'error': 'Компания не найдена'}), 404

        if user.role != 'admin' and company.owner_id != user_id:
            return jsonify({'error': 'Нет прав для удаления'}), 403

        db.session.delete(company)

        if user.role == 'employer':
            user.role = 'jobseeker'

        db.session.commit()

        return jsonify({'message': 'Компания удалена'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@company_bp.route('/industries', methods=['GET'])
def get_industries():
    industries = [
        'Информационные технологии',
        'Финансы и банки',
        'Нефть и газ',
        'Строительство',
        'Медицина и фармацевтика',
        'Образование',
        'Торговля',
        'Транспорт и логистика',
        'Производство',
        'Государственные структуры',
        'Телекоммуникации',
        'Сельское хозяйство',
        'Туризм и гостиничный бизнес',
        'Юридические услуги',
        'Маркетинг и реклама',
        'Консалтинг',
    ]
    return jsonify({'industries': industries}), 200