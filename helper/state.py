# نام فایل: helper/state.py (مدیریت وضعیت کاربر)
import logging

logger = logging.getLogger(__name__)

# وضعیت مرحله‌ای کاربران به‌صورت موقت (در یک دیکشنری در حافظه)
user_states = {}

def set_state(user_id, key, value):
    """تنظیم یک وضعیت خاص برای یک کاربر."""
    try:
        if user_id not in user_states:
            user_states[user_id] = {}
        user_states[user_id][key] = value
        logger.debug(f"Set state for user {user_id}: {key} = {value}")
    except Exception as e:
        logger.error(f"Error setting state for user {user_id}: {e}")

def get_state(user_id, key, default=None):
    """دریافت وضعیت خاص یک کاربر."""
    try:
        return user_states.get(user_id, {}).get(key, default)
    except Exception as e:
        logger.error(f"Error getting state for user {user_id}: {e}")
        return default

def clear_state(user_id):
    """حذف تمام وضعیت‌های ذخیره شده برای یک کاربر."""
    try:
        if user_id in user_states:
            user_states.pop(user_id)
            logger.debug(f"Cleared state for user {user_id}")
    except Exception as e:
        logger.error(f"Error clearing state for user {user_id}: {e}")
