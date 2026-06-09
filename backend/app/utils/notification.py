"""
Notification Service with Redis
Supports offline message persistence
"""
import redis
import json
from typing import Optional, List, Dict
from datetime import datetime

# Redis 连接
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=1,  # 使用 db1 存储通知
    password='Password123@redis',
    decode_responses=True
)


class NotificationService:
    """通知服务 - 支持离线消息暂存"""
    
    CONN_KEY_PREFIX = "ws:conn:"  # WebSocket 连接状态
    OFFLINE_QUEUE_PREFIX = "offline:queue:"  # 离线消息队列
    NOTIFICATION_HISTORY_PREFIX = "notification:history:"  # 历史记录
    
    @staticmethod
    def set_user_online(user_id: str, connection_id: str):
        """标记用户在线"""
        redis_client.setex(
            f"{NotificationService.CONN_KEY_PREFIX}{user_id}",
            3600,  # 1小时过期
            connection_id
        )
    
    @staticmethod
    def set_user_offline(user_id: str):
        """标记用户离线"""
        redis_client.delete(f"{NotificationService.CONN_KEY_PREFIX}{user_id}")
    
    @staticmethod
    def is_user_online(user_id: str) -> bool:
        """检查用户是否在线"""
        return redis_client.exists(f"{NotificationService.CONN_KEY_PREFIX}{user_id}") == 1
    
    @staticmethod
    def send_notification(user_id: str, notification: dict) -> bool:
        """
        发送通知
        如果用户在线：立即推送
        如果用户离线：存入离线队列
        """
        notification['timestamp'] = datetime.utcnow().isoformat()
        notification_json = json.dumps(notification)
        
        if NotificationService.is_user_online(user_id):
            # 用户在线，通过 WebSocket 推送（实际实现由 WebSocket handler 处理）
            redis_client.publish(f"notify:{user_id}", notification_json)
            return True
        else:
            # 用户离线，存入队列
            queue_key = f"{NotificationService.OFFLINE_QUEUE_PREFIX}{user_id}"
            redis_client.lpush(queue_key, notification_json)
            redis_client.expire(queue_key, 7 * 24 * 3600)  # 保留7天
            return False
    
    @staticmethod
    def get_offline_notifications(user_id: str) -> List[dict]:
        """获取离线消息"""
        queue_key = f"{NotificationService.OFFLINE_QUEUE_PREFIX}{user_id}"
        messages = []
        
        while True:
            msg = redis_client.rpop(queue_key)
            if not msg:
                break
            messages.append(json.loads(msg))
        
        return messages
    
    @staticmethod
    def broadcast_to_admins(notification: dict, admin_ids: Optional[List[str]] = None):
        """广播给所有管理员"""
        notification['timestamp'] = datetime.utcnow().isoformat()
        notification_json = json.dumps(notification)
        if admin_ids:
            for admin_id in admin_ids:
                NotificationService.send_notification(admin_id, notification.copy())
            return
        redis_client.publish("notify:admins", notification_json)

    @staticmethod
    def broadcast_knowledge_event(notification: dict):
        notification['timestamp'] = datetime.utcnow().isoformat()
        redis_client.publish("knowledge:events", json.dumps(notification))
    
    @staticmethod
    def _get_admin_ids() -> List[str]:
        """获取所有管理员 ID（简化版）"""
        # 实际应该从数据库查询
        # 这里返回一个占位符，实际实现需要连接数据库
        return []
    
    @staticmethod
    def create_registration_notification(username: str, user_id: str) -> dict:
        """创建注册审核通知"""
        return {
            "type": "registration_pending",
            "title": "新用户注册待审核",
            "message": f"用户 {username} 提交了注册申请，等待审核",
            "data": {
                "user_id": user_id,
                "username": username,
                "action": "review_registration"
            },
            "priority": "high"
        }
    
    @staticmethod
    def create_password_reset_notification(username: str, request_id: str) -> dict:
        """创建密码重置通知（给管理员）"""
        return {
            "type": "password_reset_pending",
            "title": "密码重置申请待审核",
            "message": f"用户 {username} 申请重置密码",
            "data": {
                "request_id": request_id,
                "username": username,
                "action": "review_password_reset"
            },
            "priority": "medium"
        }

    @staticmethod
    def create_registration_notification(username: str, user_id: str) -> dict:
        """创建注册通知（给管理员）"""
        return {
            "type": "registration_pending",
            "title": "新用户注册待审核",
            "message": f"用户 {username} 提交了注册申请",
            "data": {
                "user_id": user_id,
                "username": username,
                "action": "review_registration"
            },
            "priority": "high"
        }

    @staticmethod
    def create_approval_result_notification(user_id: str, approved: bool, type: str) -> dict:
        """创建审核结果通知给用户"""
        if type == "registration":
            return {
                "type": "registration_result",
                "title": "注册申请已通过" if approved else "注册申请被拒绝",
                "message": "您的注册申请已通过审核，现在可以登录" if approved else "您的注册申请未通过审核，请联系管理员",
                "data": {"approved": approved},
                "priority": "high"
            }
        elif type == "password_reset":
            return {
                "type": "password_reset_result",
                "title": "密码重置已通过" if approved else "密码重置申请被拒绝",
                "message": "您的密码重置申请已通过，请使用新密码登录" if approved else "您的密码重置申请被拒绝，请联系管理员",
                "data": {"approved": approved},
                "priority": "high"
            }
    
    @staticmethod
    def create_approval_result_notification(user_id: str, approved: bool, type: str) -> dict:
        """创建审核结果通知给用户"""
        if type == "registration":
            return {
                "type": "registration_result",
                "title": "注册申请已处理" if approved else "注册申请被拒绝",
                "message": "您的注册申请已通过审核，现在可以登录" if approved else "您的注册申请未通过审核，请联系管理员",
                "data": {"approved": approved},
                "priority": "high"
            }
        elif type == "password_reset":
            return {
                "type": "password_reset_result",
                "title": "密码重置申请已处理" if approved else "密码重置申请被拒绝",
                "message": "您的密码重置申请已通过，请使用新密码登录" if approved else "您的密码重置申请被拒绝，请联系管理员",
                "data": {"approved": approved},
                "priority": "high"
            }


# 全局通知服务实例
notification_service = NotificationService()
