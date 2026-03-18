"""
导出功能测试
覆盖: CSV/Excel/PDF 导出、报告导出
"""
import pytest
import json
from unittest.mock import patch, MagicMock

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers():
    return {'Authorization': 'Bearer test-token-12345'}


class TestExportCSV:
    """CSV 导出测试"""

    def test_export_csv_no_auth(self, client):
        resp = client.get('/api/export/project/1/csv')
        assert resp.status_code in [401, 403, 500]

    @patch('api.export_routes.require_auth')
    @patch('api.export_routes.get_db_connection')
    def test_export_csv_no_project(self, mock_db, mock_auth, client, auth_headers):
        mock_auth.return_value = {'user_id': 1}
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = lambda s: mock_conn
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db.return_value = mock_conn

        resp = client.get('/api/export/project/999/csv', headers=auth_headers)
        assert resp.status_code in [401, 404, 500]


class TestExportExcel:
    """Excel 导出测试"""

    def test_export_excel_no_auth(self, client):
        resp = client.get('/api/export/project/1/excel')
        assert resp.status_code in [401, 403, 500]


class TestExportPDF:
    """PDF 导出测试"""

    def test_export_pdf_no_auth(self, client):
        resp = client.get('/api/export/project/1/pdf')
        assert resp.status_code in [401, 403, 500]


class TestExportReport:
    """报告导出测试"""

    def test_export_report_no_auth(self, client):
        resp = client.get('/api/export/report/1/pdf')
        assert resp.status_code in [401, 403, 500]


class TestDataExporter:
    """DataExporter 工具类测试"""

    def test_export_to_csv_format(self):
        from utils.data_exporter import DataExporter
        exporter = DataExporter()

        test_data = [
            {'asin': 'B001', 'title': 'Product 1', 'price': 29.99},
            {'asin': 'B002', 'title': 'Product 2', 'price': 49.99},
        ]

        result = exporter.export_csv(test_data)
        assert result is not None
        assert isinstance(result, (str, bytes))

    def test_export_to_csv_empty_data(self):
        from utils.data_exporter import DataExporter
        exporter = DataExporter()
        result = exporter.export_csv([])
        assert result is not None

    def test_export_to_excel_format(self):
        from utils.data_exporter import DataExporter
        exporter = DataExporter()

        test_data = [
            {'asin': 'B001', 'title': 'Product 1', 'price': 29.99},
        ]

        result = exporter.export_excel(test_data)
        assert result is not None
        assert isinstance(result, bytes)

    def test_export_to_pdf_format(self):
        from utils.data_exporter import DataExporter
        exporter = DataExporter()

        test_data = [
            {'asin': 'B001', 'title': 'Product 1', 'price': 29.99},
        ]

        result = exporter.export_pdf(test_data)
        assert result is not None
        assert isinstance(result, bytes)

    def test_export_report_pdf(self):
        from utils.data_exporter import DataExporter
        exporter = DataExporter()

        report_data = {
            'project_name': 'Test Project',
            'total_products': 100,
            'avg_price': 35.50,
            'top_products': [
                {'asin': 'B001', 'title': 'Top 1', 'score': 95},
            ],
            'summary': 'Test report summary'
        }

        result = exporter.export_report_pdf(report_data)
        assert result is not None
        assert isinstance(result, bytes)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
