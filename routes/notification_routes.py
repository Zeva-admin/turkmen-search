from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import db
from database.models.notification import Notification
from database.models.user import User

# This module extends auth_routes with notification endpoints
# Add these routes to auth_routes.py blueprint

notification_bp = Blueprint('notifications', __name__)


@notification_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    try:
        user_id = int(get_jwt_identity())
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        limit = min(limit, 50)
        notif_type = request.args.get('type', '').strip()
        unread_only = request.args.get('unread', '').strip() == 'true'

        query = Notification.query.filter_by(user_id=user_id)

        if notif_type:
            query = query.filter_by(type=notif_type)

        if unread_only:
            query = query.filter_by(is_read=False)

        query = query.order_by(Notification.created_at.desc())

        if limit == 1:
            # Quick check for unread count
            notifications = query.limit(50).all()
            return jsonify({
                'notifications': [n.to_dict() for n in notifications],
                'total': len(notifications),
                'unread_count': sum(1 for n in notifications if not n.is_read),
            }), 200

        paginated = query.paginate(page=page, per_page=limit, error_out=False)

        return jsonify({
            'notifications': [n.to_dict() for n in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'unread_count': Notification.query.filter_by(
                user_id=user_id, is_read=False
            ).count(),
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@notification_bp.route('/notifications/read-all', methods=['POST'])
@jwt_required()
def mark_all_read():
    try:
        user_id = int(get_jwt_identity())

        Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).update({
            'is_read': True,
            'read_at': datetime.utcnow()
        })

        db.session.commit()

        return jsonify({'message': 'Все уведомления отмечены прочитанными'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера'}), 500


@notification_bp.route('/notifications/<int:notif_id>/read', methods=['PUT'])
@jwt_required()
def mark_read(notif_id):
    try:
        user_id = int(get_jwt_identity())

        notif = Notification.query.filter_by(
            id=notif_id,
            user_id=user_id
        ).first()

        if not notif:
            return jsonify({'error': 'Уведомление не найдено'}), 404

        notif.mark_read()
        db.session.commit()

        return jsonify({
            'message': 'Уведомление прочитано',
            'notification': notif.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера'}), 500


@notification_bp.route('/notifications/<int:notif_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notif_id):
    try:
        user_id = int(get_jwt_identity())

        notif = Notification.query.filter_by(
            id=notif_id,
            user_id=user_id
        ).first()

        if not notif:
            return jsonify({'error': 'Уведомление не найдено'}), 404

        db.session.delete(notif)
        db.session.commit()

        return jsonify({'message': 'Уведомление удалено'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера'}), 500