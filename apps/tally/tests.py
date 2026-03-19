from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import TallyInfo, TallyContainer


class TallyInfoModelTests(TestCase):
    def _make_tally(self, **overrides):
        data = {
            "tally_number": 1000001,
            "tally_type": "BULK",
            "crop_year": "2025/2026",
            "sd_number": "SD-1",
            "mk_number": "MK-1",
            "agent": "",
            "vessel": "VESSEL",
            "destination": "DEST",
            "terminal": "TERM",
            "loading_type": "BULK",
            "straight_type": None,
            "loading_date": date(2026, 2, 5),
            "marks_and_numbers": "M&N",
            "cocoa_type": "",
            "superintendent_type": "NONE",
            "superintendent_name": [],
            "clerk_name": ["CLERK 1"],
            "total_bags": 0,
            "total_tonnage": Decimal("0.000"),
        }
        data.update(overrides)
        return TallyInfo.objects.create(**data)

    def test_save_sets_bags_saved_for_bulk(self):
        t = self._make_tally(
            expected_bags=100, actual_bags=92, tally_type="BULK")
        t.refresh_from_db()
        self.assertEqual(t.bags_saved, 8)

    def test_save_sets_bags_saved_zero_when_missing_values(self):
        t1 = self._make_tally(expected_bags=None,
                              actual_bags=90, tally_type="BULK")
        t1.refresh_from_db()
        self.assertEqual(t1.bags_saved, 0)

        t2 = self._make_tally(
            expected_bags=100,
            actual_bags=None,
            tally_type="BULK",
            tally_number=1000002,
        )
        t2.refresh_from_db()
        self.assertEqual(t2.bags_saved, 0)

    def test_save_does_not_auto_compute_for_non_bulk(self):
        t = self._make_tally(
            tally_type="STRAIGHT_20FT",
            expected_bags=100,
            actual_bags=90,
            bags_saved=0,
        )
        t.refresh_from_db()
        self.assertEqual(t.bags_saved, 0)

    def test_str_uses_first_clerk(self):
        t = self._make_tally(clerk_name=["JOHN DOE"])
        self.assertEqual(str(t), "1000001 JOHN DOE")

    def test_get_tally_type_display_uses_choice_label(self):
        t = self._make_tally(tally_type="BULK")
        self.assertEqual(t.get_tally_type_display(), "BULK_LOADING")


class MyTalliesViewTests(TestCase):
    def _make_tally(self, tally_number, tally_type, loading_date, sd="SD-1", mk="MK-1", vessel="VESSEL", destination="DEST"):
        return TallyInfo.objects.create(
            tally_number=tally_number,
            tally_type=tally_type,
            crop_year="2025/2026",
            sd_number=sd,
            mk_number=mk,
            agent="",
            vessel=vessel,
            destination=destination,
            terminal="TERM",
            loading_type="BULK" if tally_type == "BULK" else "STRAIGHT",
            straight_type=None if tally_type == "BULK" else tally_type,
            loading_date=loading_date,
            marks_and_numbers="M&N",
            cocoa_type="",
            superintendent_type="NONE",
            superintendent_name=[],
            clerk_name=["CLERK 1"],
            total_bags=0,
            total_tonnage=Decimal("0.000"),
        )

    def test_my_tallies_renders(self):
        resp = self.client.get(reverse("my_tallies"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "tally_details/my_tallies.html")

    def test_my_tallies_paginates_5(self):
        today = timezone.localdate()
        for i in range(6):
            self._make_tally(
                tally_number=2000000 + i,
                tally_type="BULK",
                loading_date=today,
                sd=f"SD-{i}",
                mk=f"MK-{i}",
            )

        resp = self.client.get(reverse("my_tallies"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["tallies"]), 5)
        self.assertEqual(resp.context["page_obj"].paginator.per_page, 5)

    def test_my_tallies_search_filters_results(self):
        today = timezone.localdate()
        t1 = self._make_tally(3000001, "BULK", today, vessel="OCEAN STAR")
        t2 = self._make_tally(3000002, "STRAIGHT_20FT",
                              today, vessel="ANOTHER VESSEL")

        resp = self.client.get(reverse("my_tallies"), {"q": "OCEAN"})
        html = resp.content.decode("utf-8")
        self.assertIn(str(t1.tally_number), html)
        self.assertNotIn(str(t2.tally_number), html)

    def test_my_tallies_period_today_filters_by_loading_date(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        self._make_tally(4000001, "BULK", today)
        self._make_tally(4000002, "BULK", yesterday)

        resp = self.client.get(reverse("my_tallies"), {"period": "today"})
        html = resp.content.decode("utf-8")
        self.assertIn("4000001", html)
        self.assertNotIn("4000002", html)

    def test_my_tallies_period_week_includes_last_7_days(self):
        today = timezone.localdate()
        in_range = today - timedelta(days=6)
        out_range = today - timedelta(days=10)

        self._make_tally(5000001, "BULK", in_range)
        self._make_tally(5000002, "BULK", out_range)

        resp = self.client.get(reverse("my_tallies"), {"period": "week"})
        html = resp.content.decode("utf-8")
        self.assertIn("5000001", html)
        self.assertNotIn("5000002", html)

    def test_my_tallies_sort_oldest_orders_by_date_created(self):
        today = timezone.localdate()
        a = self._make_tally(6000001, "BULK", today, sd="SD-9", mk="MK-9")
        b = self._make_tally(6000002, "BULK", today, sd="SD-1", mk="MK-1")

        resp = self.client.get(reverse("my_tallies"), {"sort": "oldest"})
        html = resp.content.decode("utf-8")

        pos_a = html.find(str(a.tally_number))
        pos_b = html.find(str(b.tally_number))
        self.assertTrue(pos_a < pos_b)

    def test_my_tallies_sort_sd_orders_by_sd_then_mk(self):
        today = timezone.localdate()
        self._make_tally(7000001, "BULK", today, sd="SD-2", mk="MK-1")
        self._make_tally(7000002, "BULK", today, sd="SD-1", mk="MK-9")

        resp = self.client.get(reverse("my_tallies"), {"sort": "sd"})
        html = resp.content.decode("utf-8")

        pos_first = html.find("7000002")
        pos_second = html.find("7000001")
        self.assertTrue(pos_first < pos_second)

    def test_my_tallies_contains_tally_number_link_to_view(self):
        today = timezone.localdate()
        t = self._make_tally(8000001, "BULK", today)

        resp = self.client.get(reverse("my_tallies"))
        expected_href = reverse("tally_view", kwargs={"pk": t.id})
        self.assertContains(resp, f'href="{expected_href}"')


class TallyViewTests(TestCase):
    def _make_tally(self):
        return TallyInfo.objects.create(
            tally_number=9000001,
            tally_type="BULK",
            crop_year="2025/2026",
            sd_number="SD-1",
            mk_number="MK-1",
            agent="",
            vessel="VESSEL",
            destination="DEST",
            terminal="TERM",
            loading_type="BULK",
            straight_type=None,
            loading_date=timezone.localdate(),
            marks_and_numbers="M&N",
            cocoa_type="",
            superintendent_type="NONE",
            superintendent_name=[],
            clerk_name=["CLERK 1"],
            total_bags=0,
            total_tonnage=Decimal("0.000"),
        )

    def test_tally_view_200(self):
        t = self._make_tally()
        resp = self.client.get(reverse("tally_view", kwargs={"pk": t.id}))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "tally_details/tally_digital.html")

    def test_tally_view_404_for_missing(self):
        resp = self.client.get(reverse("tally_view", kwargs={"pk": 999999}))
        self.assertEqual(resp.status_code, 404)


class ExportTests(TestCase):
    def _make_tally_with_container(self, tally_type="BULK"):
        t = TallyInfo.objects.create(
            tally_number=9100001 if tally_type == "BULK" else 9100002,
            tally_type=tally_type,
            crop_year="2025/2026",
            sd_number="SD-1",
            mk_number="MK-1",
            agent="",
            vessel="VESSEL",
            destination="DEST",
            terminal="TERM",
            loading_type="BULK" if tally_type == "BULK" else "STRAIGHT",
            straight_type=None if tally_type == "BULK" else tally_type,
            loading_date=timezone.localdate(),
            marks_and_numbers="M&N",
            cocoa_type="GRADE I",
            superintendent_type="NONE",
            superintendent_name=[],
            clerk_name=["CLERK 1"],
            total_bags=10,
            total_tonnage=Decimal("0.625"),
        )

        TallyContainer.objects.create(
            tally=t,
            container_number="CONT-1",
            seal_number="SEAL-1",
            tonnage=Decimal("0.625"),
            bags_cut=10 if tally_type == "BULK" else None,
            bags=10,
            container_photo="pics/containers/dummy.jpg",
            seal_photo="pics/seals/dummy.jpg",
        )
        return t

    @patch("tally.views.workbook_to_bytes", return_value=b"fake-xlsx-bytes")
    @patch("tally.views.build_tally_excel_from_template")
    def test_export_tally_excel_returns_xlsx(self, mock_builder, mock_to_bytes):
        class _WS(dict):
            sheetnames = ["NEW"]

            def __setitem__(self, key, value):
                super().__setitem__(key, value)

        class _WB:
            sheetnames = ["NEW"]

        wb = _WB()
        ws = _WS()
        mock_builder.return_value = (wb, ws, "/tmp/template.xlsx")

        t = self._make_tally_with_container("BULK")
        resp = self.client.get(
            reverse("export_tally_excel", kwargs={"tally_id": t.id}))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(len(resp.content) > 0)

    def test_tally_pdf_returns_pdf(self):
        t = self._make_tally_with_container("BULK")
        resp = self.client.get(reverse("tally_pdf", kwargs={"pk": t.id}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(len(resp.content) > 0)
