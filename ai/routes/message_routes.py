from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import db
from database.models.message import Message, Conversation
from database.models.user import User
from database.models.notification import Notification

message_bp = Blueprint('messages', __name__)


def get_or_create_conversation(user1_id, user2_id):
    ids = sorted([user1_id, user2_id])
    conv_id = f'conv_{ids[0]}_{ids[1]}'

    conversation = Conversation.query.filter_by(conversation_id=conv_id).first()
    if not conversation:
        conversation = Conversation(
            conversation_id=conv_id,
            user1_id=ids[0],
            user2_id=ids[1],
        )
        db.session.add(conversation)
        db.session.flush()

    return conversation


@message_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    try:
        user_id = int(get_jwt_identity())

        conversations = Conversation.query.filter(
            (Conversation.user1_id == user_id) |
            (Conversation.user2_id == user_id)
        ).order_by(Conversation.last_message_at.desc()).all()

        return jsonify({
            'conversations': [c.to_dict(user_id) for c in conversations],
            'total': len(conversations),
        }), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@message_bp.route('/conversation/<int:other_user_id>', methods=['GET'])
@jwt_required()
def get_conversation_messages(other_user_id):
    try:
        user_id = int(get_jwt_identity())

        other_user = User.query.get(other_user_id)
        if not other_user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        conversation = get_or_create_conversation(user_id, other_user_id)
        db.session.commit()

        page = request.args.get('page', 1, type=int)

        messages = Message.query.filter_by(
            conversation_id=conversation.conversation_id
        ).filter(
            ~(
                (Message.sender_id == user_id) & (Message.is_deleted_sender == True)
            ) &
            ~(
                (Message.receiver_id == user_id) & (Message.is_deleted_receiver == True)
            )
        ).order_by(Message.created_at.asc()).paginate(
            page=page, per_page=50, error_out=False
        )

        # Mark as read
        unread = Message.query.filter_by(
            conversation_id=conversation.conversation_id,
            receiver_id=user_id,
            is_read=False,
        ).all()

        for msg in unread:
            msg.is_read = True
            msg.read_at = datetime.utcnow()

        # Reset unread count
        if conversation.user1_id == user_id:
            conversation.unread_count_user1 = 0
        else:
            conversation.unread_count_user2 = 0

        db.session.commit()

        return jsonify({
            'messages': [m.to_dict(user_id) for m in messages.items],
            'total': messages.total,
            'pages': messages.pages,
            'current_page': page,
            'other_user': {
                'id': other_user.id,
                'name': other_user.name,
                'avatar': other_user.avatar,
                'role': other_user.role,
            },
            'conversation_id': conversation.conversation_id,
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@message_bp.route('/send', methods=['POST'])
@jwt_required()
def send_message():
    try:
        user_id = int(get_jwt_identity())
        sender = User.query.get(user_id)

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Данные не предоставлены'}), 400

        receiver_id = data.get('receiver_id')
        text = data.get('text', '').strip()

        if not receiver_id:
            return jsonify({'error': 'Получатель обязателен'}), 400
        if not text:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
        if len(text) > 5000:
            return jsonify({'error': 'Сообщение слишком длинное'}), 400

        if receiver_id == user_id:
            return jsonify({'error': 'Нельзя отправить сообщение самому себе'}), 400

        receiver = User.query.get(receiver_id)
        if not receiver:
            return jsonify({'error': 'Получатель не найден'}), 404

        conversation = get_or_create_conversation(user_id, receiver_id)

        message = Message(
            sender_id=user_id,
            receiver_id=receiver_id,
            text=text,
            conversation_id=conversation.conversation_id,
        )
        db.session.add(message)

        # Update conversation
        conversation.last_message = text[:100]
        conversation.last_message_at = datetime.utcnow()

        if conversation.user1_id == receiver_id:
            conversation.unread_count_user1 += 1
        else:
            conversation.unread_count_user2 += 1

        # Notify receiver
        Notification.create_notification(
            user_id=receiver_id,
            title='Новое сообщение',
            text=f'{sender.name}: {text[:80]}...' if len(text) > 80 else f'{sender.name}: {text}',
            type='message',
            link='/messages',
            link_text='Открыть сообщения',
        )

        db.session.commit()

        return jsonify({
            'message': 'Сообщение отправлено',
            'data': message.to_dict(user_id)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера', 'detail': str(e)}), 500


@message_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    try:
        user_id = int(get_jwt_identity())

        count = Message.query.filter_by(
            receiver_id=user_id,
            is_read=False,
        ).count()

        return jsonify({'unread_count': count}), 200

    except Exception as e:
        return jsonify({'error': 'Ошибка сервера'}), 500


@message_bp.route('/<int:message_id>', methods=['DELETE'])
@jwt_required()
def delete_message(message_id):
    try:
        user_id = int(get_jwt_identity())
        message = Message.query.get(message_id)

        if not message:
            return jsonify({'error': 'Сообщение не найдено'}), 404

        if message.sender_id == user_id:
            message.is_deleted_sender = True
        elif message.receiver_id == user_id:
            message.is_deleted_receiver = True
        else:
            return jsonify({'error': 'Нет прав для удаления'}), 403

        if message.is_deleted_sender and message.is_deleted_receiver:
            db.session.delete(message)
        
        db.session.commit()

        return jsonify({'message': 'Сообщение удалено'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Ошибка сервера'}), 500