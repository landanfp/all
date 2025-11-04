# نام فایل: helper/state.py (مدیریت وضعیت کاربر)
# وضعیت مرحله‌ای کاربران به‌صورت موقت (در یک دیکشنری در حافظه)
user_states = {}

def set_state(user_id, key, value):
    """تنظیم یک وضعیت خاص برای یک کاربر."""
    if user_id not in user_states:
        user_states[user_id] = {}
    user_states[user_id][key] = value

def get_state(user_id, key, default=None):
    """دریافت وضعیت خاص یک کاربر."""
    return user_states.get(user_id, {}).get(key, default)

def clear_state(user_id):
    """حذف تمام وضعیت‌های ذخیره شده برای یک کاربر."""
    if user_id in user_states:
        user_states.pop(user_id)
