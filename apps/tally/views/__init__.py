"""Tally app views.

Grouped by feature to keep the codebase maintainable.
"""

from .create import (
    bulk,
    japan,
    loading,
    new_tally,
    normal_straight,
    straight_20,
    straight_loading_options,
    tally_success,
)
from .lists import my_tallies
from .detail import tally_delete, tally_edit, tally_excel, tally_pdf, tally_view
from .pdf_export import tally_pdf_download
from .approval import (
    all_approved_tallies,
    approve_recall_request,
    approve_tally,
    reject_recall_request,
    reject_tally,
    request_recall,
    recall_tally,
    submit_tally,
)
from .pending import pending_tallies
from .exports import export_tally_excel
