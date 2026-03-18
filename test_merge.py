from app import create_app
app = create_app()
client = app.test_client()

# Test all pages still render
pages = ['/auth', '/dashboard', '/projects/new', '/projects/test-123',
         '/products/B0TEST/analysis', '/market', '/profit', '/3d-lab',
         '/settings/api-keys', '/settings/subscription', '/settings/ai', '/reports/test-123']
for page in pages:
    resp = client.get(page)
    status = resp.status_code
    ok = 'OK' if status in (200, 302) else 'FAIL'
    print(f'  [{ok}] {page} -> {status}')

print()
# Test new API endpoints
new_apis = ['/api/subscription/plans', '/api/docs', '/api/i18n/en_US',
            '/api/i18n/zh_CN', '/api/i18n/ko_KR', '/api/metrics']
for api_path in new_apis:
    resp = client.get(api_path)
    ok = 'OK' if resp.status_code == 200 else 'FAIL'
    print(f'  [{ok}] {api_path} -> {resp.status_code}')

print()
# Test new API routes exist
new_routes = [
    ('GET', '/api/v1/export/products/1?format=csv'),
    ('GET', '/api/v1/export/report/1?format=pdf'),
    ('GET', '/api/v1/teams'),
    ('GET', '/api/v1/notifications'),
    ('GET', '/api/v1/audit/logs'),
    ('GET', '/api/sse/tasks'),
    ('GET', '/api/apm/stats'),
    ('GET', '/api/cleanup/stats'),
]
for method, path in new_routes:
    if method == 'GET':
        resp = client.get(path)
    else:
        resp = client.post(path)
    # 401 means route exists but needs auth, which is expected
    ok = 'OK' if resp.status_code in (200, 401, 403) else 'WARN'
    print(f'  [{ok}] {method} {path} -> {resp.status_code}')
