"""
سكربت استيراد بيانات التنبؤ (P10/P50/P90) داخل جدول Forecasts
====================================================================
يشتغل كأمر Django: python manage.py import_forecasts

ضعه بالمسار: dashboard/management/commands/import_forecasts.py
(نفس مجلد commands اللي فيه import_data.py و simulate_stream.py)

قبل التشغيل: انسخي ملف django_forecast_import.csv (من نتيجة النوتبوك)
إلى جذر مشروع EnerTrack (نفس مكان manage.py)
"""

import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from dashboard.models import ModelRegistry, Forecast


class Command(BaseCommand):
    help = "يستورد بيانات django_forecast_import.csv (نتيجة النوتبوك) لجدول Forecasts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", type=str, default="django_forecast_import.csv",
            help="مسار ملف الـCSV (افتراضيًا: django_forecast_import.csv بجذر المشروع)"
        )

    def handle(self, *args, **options):
        filepath = options["file"]
        self.stdout.write(self.style.SUCCESS(f"بدء استيراد التنبؤات من: {filepath}"))

        model_reg, _ = ModelRegistry.objects.get_or_create(
            model_version="xgb_quantile_forecaster_v1",
            defaults={"model_type": "regressor"},
        )

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.stdout.write(f"عدد الأيام بالملف: {len(rows)}")

        created = 0
        with transaction.atomic():
            for row in rows:
                target_date = datetime.strptime(row["target_date"], "%Y-%m-%d").date()
                Forecast.objects.update_or_create(
                    target_date=target_date,
                    model_version=model_reg,
                    defaults={
                        "p10": float(row["p10"]),
                        "p50": float(row["p50"]),
                        "p90": float(row["p90"]),
                        "actual_value": float(row["actual_value"]),
                    },
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"\nخلص الاستيراد بنجاح: {created} يوم تنبؤ"))
        