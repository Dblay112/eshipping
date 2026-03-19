"""Operations app views.

This package provides a maintainable structure by grouping views by feature.
URLs should import view callables from this package.
"""

from .api import sd_search_json, sd_details_json, client_error_report, allocations_for_sd
from .containers import container_list_view, container_list_delete
from .daily_port import daily_port_view, daily_port_create, daily_port_edit, daily_port_delete
from .schedule import schedule_view, schedule_create, schedule_edit, schedule_delete
from .sd_records import operations_list, sd_create, sd_edit, sd_detail, sd_export_excel, sd_record_delete
from .terminal_schedule import (
    terminal_schedule_list,
    terminal_schedule_create,
    terminal_schedule_edit,
    terminal_schedule_delete,
)
from .work_program import work_program_list, work_program_create, work_program_edit, work_program_delete
