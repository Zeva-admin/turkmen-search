from flask import Blueprint, render_template

page_bp = Blueprint('pages', __name__)


@page_bp.route('/')
def index():
    return render_template('index.html')


@page_bp.route('/jobs')
def jobs():
    return render_template('jobs.html')


@page_bp.route('/jobs/<int:job_id>')
def job_page(job_id):
    return render_template('job_page.html', job_id=job_id)


@page_bp.route('/companies')
def companies():
    return render_template('companies.html')


@page_bp.route('/companies/<int:company_id>')
def company_page(company_id):
    return render_template('company_page.html', company_id=company_id)


@page_bp.route('/login')
def login():
    return render_template('login.html')


@page_bp.route('/register')
def register():
    return render_template('register.html')


@page_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@page_bp.route('/profile')
def profile():
    return render_template('profile.html')


@page_bp.route('/create-job')
def create_job():
    return render_template('create_job.html')


@page_bp.route('/create-resume')
def create_resume():
    return render_template('create_resume.html')


@page_bp.route('/resumes')
def resumes():
    return render_template('resumes.html')


@page_bp.route('/resumes/<int:resume_id>')
def resume_page(resume_id):
    return render_template('resume_page.html', resume_id=resume_id)


@page_bp.route('/messages')
def messages():
    return render_template('messages.html')


@page_bp.route('/notifications')
def notifications():
    return render_template('notifications.html')


@page_bp.route('/settings')
def settings():
    return render_template('settings.html')