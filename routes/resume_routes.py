from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import db
from database.models.resume import Resume, Experience, Education, Language
from database.models.user import User
import json

resume_bp = Blueprint('resumes', __name__)


@resume_bp.route('', methods=['GET'])
def get_resumes():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 50)

        query = Resume.query.filter_by(is_active=True, is_public=True)

        search = request.args.get('q', '').strip()
        if search:
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Resume.title.ilike(f'%{search}%'),
                    Resume.desired_position.ilike(f'%{search}%'),
                    Resume.skills.ilike(f'%{search}%'),
                )
            )

        city = request.args.get('city', '').strip()
        if city:
            query = query.filter(Resume.city == city)

        employment_type = request.args.get('employment_type', '').strip()
        if employment_type:
            query = query.filter(Resume.employment_type == employment_type)

        salary_from = request.args.get('salary_from', type=int)
        if salary_from:
            query = query.filter(Resume.desired_salary >= salary_from)

        salary_to = request.args.get('salary_to', type=int)
        if salary_to:
            query = query.filter(Resume.desired_salary <= salary_to)

        sort = request.args.get('sort', 'date')
        if sort == 'salary':
            query = query.order_by(Resume.desired_salary.desc().nullslast())
        else:
            query = query.order_by(Resume.updated_at.desc())

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'resumes': [r.to_dict() for r in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': paginated.has_next,
            'has_prev': paginated.has_prev,
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@resume_bp.route('/<int:resume_id>', methods=['GET'])
def get_resume(resume_id):
    try:
        resume = Resume.query.get(resume_id)
        if not resume or not resume.is_active:
            return jsonify({'error': 'Резюме не найдено'}), 404

        if not resume.is_public:
            return jsonify({'error': 'Резюме недоступно'}), 403

        resume.views_count += 1
        db.session.commit()

        return jsonify({'resume': resume.to_dict(full=True)}), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@resume_bp.route('', methods=['POST'])
@jwt_required()
def create_resume():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        errors = {}
        if not data.get('title', '').strip():
            errors['title'] = 'Заголовок резюме обязателен'
        if not data.get('first_name', '').strip():
            errors['first_name'] = 'Имя обязательно'
        if not data.get('last_name', '').strip():
            errors['last_name'] = 'Фамилия обязательна'

        if errors:
            return jsonify({'error': 'Ошибка валидации', 'fields': errors}), 422

        skills = data.get('skills', [])
        if isinstance(skills, list):
            skills = json.dumps(skills, ensure_ascii=False)

        resume = Resume(
            user_id=user_id,
            title=data['title'].strip(),
            desired_position=data.get('desired_position', '').strip(),
            desired_salary=data.get('desired_salary'),
            salary_currency=data.get('salary_currency', 'TMT'),
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            middle_name=data.get('middle_name', '').strip(),
            city=data.get('city', '').strip(),
            phone=data.get('phone', '').strip(),
            email=data.get('email', '').strip(),
            about=data.get('about', '').strip(),
            skills=skills,
            employment_type=data.get('employment_type', ''),
            schedule=data.get('schedule', ''),
            relocation=data.get('relocation', False),
            business_trip=data.get('business_trip', False),
            is_public=data.get('is_public', True),
        )

        if data.get('birth_date'):
            try:
                resume.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            except ValueError:
                pass

        db.session.add(resume)
        db.session.flush()

        # Add experiences
        for exp_data in data.get('experiences', []):
            if exp_data.get('company_name') and exp_data.get('position'):
                exp = Experience(
                    resume_id=resume.id,
                    company_name=exp_data['company_name'].strip(),
                    position=exp_data['position'].strip(),
                    city=exp_data.get('city', '').strip(),
                    is_current=exp_data.get('is_current', False),
                    description=exp_data.get('description', '').strip(),
                )
                if exp_data.get('start_date'):
                    try:
                        exp.start_date = datetime.strptime(exp_data['start_date'], '%Y-%m-%d').date()
                    except ValueError:
                        pass
                if exp_data.get('end_date') and not exp_data.get('is_current'):
                    try:
                        exp.end_date = datetime.strptime(exp_data['end_date'], '%Y-%m-%d').date()
                    except ValueError:
                        pass
                db.session.add(exp)

        # Add educations
        for edu_data in data.get('educations', []):
            if edu_data.get('institution'):
                edu = Education(
                    resume_id=resume.id,
                    institution=edu_data['institution'].strip(),
                    faculty=edu_data.get('faculty', '').strip(),
                    specialty=edu_data.get('specialty', '').strip(),
                    degree=edu_data.get('degree', '').strip(),
                    start_year=edu_data.get('start_year'),
                    end_year=edu_data.get('end_year'),
                    is_current=edu_data.get('is_current', False),
                )
                db.session.add(edu)

        # Add languages
        for lang_data in data.get('languages', []):
            if lang_data.get('name') and lang_data.get('level'):
                lang = Language(
                    resume_id=resume.id,
                    name=lang_data['name'].strip(),
                    level=lang_data['level'],
                )
                db.session.add(lang)

        db.session.commit()

        return jsonify({
            'message': 'Резюме создано успешно',
            'resume': resume.to_dict(full=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@resume_bp.route('/<int:resume_id>', methods=['PUT'])
@jwt_required()
def update_resume(resume_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        resume = Resume.query.get(resume_id)

        if not resume:
            return jsonify({'error': 'Резюме не найдено'}), 404

        if user.role != 'admin' and resume.user_id != user_id:
            return jsonify({'error': 'Нет прав для редактирования'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        updatable = [
            'title', 'desired_position', 'desired_salary', 'salary_currency',
            'first_name', 'last_name', 'middle_name', 'city', 'phone',
            'email', 'about', 'employment_type', 'schedule',
            'relocation', 'business_trip', 'is_active', 'is_public'
        ]

        for field in updatable:
            if field in data:
                value = data[field]
                if isinstance(value, str):
                    value = value.strip()
                setattr(resume, field, value)

        if 'skills' in data:
            skills = data['skills']
            if isinstance(skills, list):
                skills = json.dumps(skills, ensure_ascii=False)
            resume.skills = skills

        if 'birth_date' in data and data['birth_date']:
            try:
                resume.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            except ValueError:
                pass

        # Update experiences
        if 'experiences' in data:
            Experience.query.filter_by(resume_id=resume.id).delete()
            for exp_data in data['experiences']:
                if exp_data.get('company_name') and exp_data.get('position'):
                    exp = Experience(
                        resume_id=resume.id,
                        company_name=exp_data['company_name'].strip(),
                        position=exp_data['position'].strip(),
                        city=exp_data.get('city', '').strip(),
                        is_current=exp_data.get('is_current', False),
                        description=exp_data.get('description', '').strip(),
                    )
                    if exp_data.get('start_date'):
                        try:
                            exp.start_date = datetime.strptime(exp_data['start_date'], '%Y-%m-%d').date()
                        except ValueError:
                            pass
                    if exp_data.get('end_date') and not exp_data.get('is_current'):
                        try:
                            exp.end_date = datetime.strptime(exp_data['end_date'], '%Y-%m-%d').date()
                        except ValueError:
                            pass
                    db.session.add(exp)

        # Update educations
        if 'educations' in data:
            Education.query.filter_by(resume_id=resume.id).delete()
            for edu_data in data['educations']:
                if edu_data.get('institution'):
                    edu = Education(
                        resume_id=resume.id,
                        institution=edu_data['institution'].strip(),
                        faculty=edu_data.get('faculty', '').strip(),
                        specialty=edu_data.get('specialty', '').strip(),
                        degree=edu_data.get('degree', '').strip(),
                        start_year=edu_data.get('start_year'),
                        end_year=edu_data.get('end_year'),
                        is_current=edu_data.get('is_current', False),
                    )
                    db.session.add(edu)

        # Update languages
        if 'languages' in data:
            Language.query.filter_by(resume_id=resume.id).delete()
            for lang_data in data['languages']:
                if lang_data.get('name') and lang_data.get('level'):
                    lang = Language(
                        resume_id=resume.id,
                        name=lang_data['name'].strip(),
                        level=lang_data['level'],
                    )
                    db.session.add(lang)

        resume.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Резюме обновлено',
            'resume': resume.to_dict(full=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@resume_bp.route('/<int:resume_id>', methods=['DELETE'])
@jwt_required()
def delete_resume(resume_id):
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        resume = Resume.query.get(resume_id)

        if not resume:
            return jsonify({'error': 'Резюме не найдено'}), 404

        if user.role != 'admin' and resume.user_id != user_id:
            return jsonify({'error': 'Нет прав для удаления'}), 403

        db.session.delete(resume)
        db.session.commit()

        return jsonify({'message': 'Резюме удалено'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@resume_bp.route('/my', methods=['GET'])
@jwt_required()
def get_my_resumes():
    try:
        user_id = int(get_jwt_identity())
        resumes = Resume.query.filter_by(
            user_id=user_id
        ).order_by(Resume.updated_at.desc()).all()

        return jsonify({
            'resumes': [r.to_dict(full=True) for r in resumes],
            'total': len(resumes)
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500