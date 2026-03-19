"""Ebooking app views.

Grouped by feature to keep the codebase maintainable.
"""

from .lists import booking_list, assigned_sds_list
from .create import booking_create
from .detail import booking_edit, booking_detail_delete
from .corrections import booking_add_correction, booking_correction_history
from .api import booking_data_json, debug_model_config

__all__ = [
    'booking_list',
    'assigned_sds_list',
    'booking_create',
    'booking_edit',
    'booking_detail_delete',
    'booking_add_correction',
    'booking_correction_history',
    'booking_data_json',
    'debug_model_config',
]
